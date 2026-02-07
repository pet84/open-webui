# AIRIS Image Pipeline – opravený plugin

Plugin generuje obrázky přes OpenAI API (model `gpt-image-1` nebo DALL·E).  
Tento soubor obsahuje **opravenou verzi** kódu od ChatGPT.

## Co bylo špatně v původním kódu

1. **Špatný endpoint** – používal se `{base}/images`, správně je **`{base}/images/generations`** (generování) a pro úpravu obrázku **`{base}/images/edits`**.
2. **Generations API nebere parametr `image`** – přidání `payload["image"] = image_url` u generování je neplatné; úprava obrázku se dělá zvláštním voláním na `/images/edits` s polem `images` (viz dokumentace OpenAI).
3. **Obsah zprávy** – v Open WebUI může být `content` pole zprávy **pole částí** (např. `[{ "type": "text", "text": "..." }]`), ne jen řetězec; je potřeba z něj vybrat text.
4. **Synchronní `requests`** – v async funkci je vhodné používat **aiohttp**, aby se neblokovala smyčka.

## Kód pluginu (opravená verze)

Pro použití v Open WebUI zkopíruj celý blok kódu níže (od trojitých uvozovek včetně docstringu až po konec třídy). První řádek souboru musí být `"""`.

```python
"""
title: AIRIS Image Pipeline
author: Petr Kvasnička / AIRIS
author_url: https://archenergy.cz
version: 1.0.0
openwebui_id: airis-image-pipeline
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjN0FDOTQzIiBzdHJva2Utd2lkdGg9IjIiIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHJlY3QgeD0iMyIgeT0iMyIgd2lkdGg9IjE4IiBoZWlnaHQ9IjE4IiByeD0iMiIvPjxwYXRoIGQ9Ik03IDEyIDkgMTQgMTcgNiIvPjwvc3ZnPg==
description: AIRIS avatar generator – OpenAI gpt-image-1 pipeline pro sjednocenou AI identitu.
"""

import aiohttp
from typing import Optional
from pydantic import BaseModel, Field


def _get_text_from_content(content) -> str:
    """Z message['content'] (řetězec nebo pole částí) vrátí čistý text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return (part.get("text") or "").strip()
    return ""


def _get_last_user_message_content(messages: list) -> str:
    """Vrátí text poslední zprávy od uživatele."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return _get_text_from_content(msg.get("content"))
    return ""


def _get_reference_image_url(messages: list) -> Optional[str]:
    """V historii chatu najde první obrázek (od nejnovější zprávy)."""
    for msg in reversed(messages):
        for f in msg.get("files") or []:
            if f.get("type") == "image" or (f.get("content_type") or "").startswith("image/"):
                url = f.get("url")
                if url:
                    return url
    return None


class Action:

    class Valves(BaseModel):
        openai_api_key: str = Field(
            default="",
            description="OpenAI API klíč (sk-...)"
        )
        openai_api_base: str = Field(
            default="https://api.openai.com/v1",
            description="OpenAI API base URL"
        )
        image_model: str = Field(
            default="gpt-image-1",
            description="Model pro obrázky (doporučeno gpt-image-1)"
        )
        image_size: str = Field(
            default="1024x1024",
            description="Velikost obrázku (např. 1024x1024, 1536x1024, 1024x1536)"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.file_handler = True

    async def action(
        self,
        body: dict,
        __event_emitter__=None,
        __user__=None,
        **kwargs
    ) -> Optional[dict]:
        messages = body.get("messages", [])
        if not messages:
            return None

        prompt = _get_last_user_message_content(messages)
        if not prompt:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Žádný text v zprávě.", "done": True},
                })
            return None

        image_url = _get_reference_image_url(messages)
        base = (self.valves.openai_api_base or "").rstrip("/")
        api_key = (self.valves.openai_api_key or "").strip()
        if not api_key:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Chyba: Není nastaven OpenAI API klíč.", "done": True},
                })
            return None

        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": f"AIRIS Image Pipeline → {self.valves.image_model}",
                    "done": False,
                },
            })

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            if image_url:
                # Úprava obrázku: endpoint /images/edits, tělo s polem images
                url = f"{base}/images/edits"
                payload = {
                    "model": self.valves.image_model,
                    "prompt": prompt,
                    "images": [{"image_url": {"url": image_url}}],
                    "size": self.valves.image_size,
                }
            else:
                # Nový obrázek: endpoint /images/generations
                url = f"{base}/images/generations"
                payload = {
                    "model": self.valves.image_model,
                    "prompt": prompt,
                    "n": 1,
                    "size": self.valves.image_size,
                }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    result = await resp.json()

                    if resp.status >= 400:
                        err = result.get("error", {})
                        msg = err.get("message", err.get("code", "Image API error"))
                        raise RuntimeError(msg)

                    if "data" not in result or not result["data"]:
                        raise RuntimeError("API nevrátilo žádný obrázek.")

                    item = result["data"][0]
                    image_b64 = item.get("b64_json")
                    if not image_b64:
                        # DALL·E může vracet url
                        img_url = item.get("url")
                        if img_url and __event_emitter__:
                            await __event_emitter__({
                                "type": "message",
                                "data": {"content": f"![AIRIS]({img_url})"},
                            })
                        else:
                            raise RuntimeError("Odpověď neobsahuje b64_json ani url.")
                    else:
                        if __event_emitter__:
                            await __event_emitter__({
                                "type": "message",
                                "data": {
                                    "content": f"![AIRIS Avatar](data:image/png;base64,{image_b64})",
                                },
                            })

                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {"description": "Avatar vygenerován", "done": True},
                        })

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": f"Chyba: {str(e)}",
                        "done": True,
                    },
                })

        return None
```

## Nastavení ve Valves

- **openai_api_key** – OpenAI API klíč (sk-…).
- **openai_api_base** – např. `https://api.openai.com/v1` (nebo vlastní proxy).
- **image_model** – např. `gpt-image-1`, `gpt-image-1-mini`, `dall-e-3`, `dall-e-2`.
- **image_size** – např. `1024x1024`, `1536x1024`, `1024x1536` (u GPT Image i `auto`).

## Poznámky

- **Generování**: pouze text v poslední uživatelské zprávě → volá se `/images/generations`.
- **Úprava obrázku**: pokud je v chatu připojen obrázek (soubor), použije se `/images/edits` s referenčním obrázkem.
- Modely GPT Image vrací obrázek v `b64_json`; DALL·E může vracet `url` – plugin obě varianty zvládne.
