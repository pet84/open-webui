"""Fork (Airis): velká znalostní báze z URL na začátek system promptu, se značkou cache.

Agent si o ni řekne vlastním parametrem (Pokročilé parametry → vlastní parametr):

    cached_context = {"url": "https://…/kb.txt", "prefix": "Text před znalostní bází\\n"}

Proč až v routeru a ne filtrem: filtry i middleware (Dnešní datum s časem na minuty,
paměť, dovednosti…) přidávají text na ZAČÁTEK systémové zprávy a middleware ji nakonec
slévá do jednoho řetězce. Značka cache by se ztratila a prefix by se měnil každou minutu.
Tady je to poslední krok před odesláním, takže znalostní báze je vždy úplně první.

U Claude přes OpenRouter (model `anthropic/…`) dostane blok `cache_control`, takže se
~120k tokenů platí plně jen jednou za 5 minut, jinak za desetinu. Ostatním providerům
se báze jen vloží jako text (neznámé pole by mohly odmítnout).
"""

import logging
import time

import aiohttp

log = logging.getLogger(__name__)

PARAM = 'cached_context'
FETCH_TTL_SECONDS = 600
_documents: dict[str, tuple[float, str]] = {}


async def _fetch_document(url: str) -> str:
    cached = _documents.get(url)
    if cached and time.time() - cached[0] < FETCH_TTL_SECONDS:
        return cached[1]
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                text = (await response.read()).decode('utf-8', errors='replace').lstrip('﻿')
    except Exception as e:
        if cached:
            log.warning('cached_context: %s nejde stáhnout (%s), použita starší kopie', url, e)
            return cached[1]
        raise RuntimeError(f'Znalostní bázi se nepodařilo načíst: {e}') from e
    if not text.strip():
        raise RuntimeError('Znalostní báze je prázdná')
    _documents[url] = (time.time(), text)
    return text


def supports_cache_control(model_id: str, url: str) -> bool:
    return 'openrouter.ai' in url and str(model_id).startswith('anthropic/')


async def apply_cached_context(payload: dict, url: str) -> dict:
    config = payload.pop(PARAM, None)
    if not config:
        return payload
    if isinstance(config, str):
        config = {'url': config}
    if not isinstance(config, dict) or not config.get('url'):
        log.warning('cached_context: chybí url, parametr ignorován')
        return payload

    document = await _fetch_document(config['url'])
    context = f'{config.get("prefix") or ""}{document}'.strip()

    messages = payload.setdefault('messages', [])
    system = messages[0] if messages and messages[0].get('role') == 'system' else None

    if supports_cache_control(payload.get('model', ''), url):
        blocks = [{'type': 'text', 'text': context, 'cache_control': {'type': 'ephemeral'}}]
        if system:
            content = system.get('content')
            if isinstance(content, list):
                blocks.extend(content)
            elif content:
                blocks.append({'type': 'text', 'text': content})
            system['content'] = blocks
        else:
            messages.insert(0, {'role': 'system', 'content': blocks})
    elif system:
        content = system.get('content')
        if isinstance(content, list):
            system['content'] = [{'type': 'text', 'text': context}, *content]
        else:
            system['content'] = f'{context}\n\n{content}' if content else context
    else:
        messages.insert(0, {'role': 'system', 'content': context})

    return payload
