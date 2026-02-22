"""
title: Anthropic Claude API
author: 1337Hero (Mike Key)
version: 2.1.0
license: MIT
required_open_webui_version: 0.5.0
requirements: requests>=2.31.0

Jednoduchá integrace Anthropic Claude – jen to potřebné.
Bezpečnost od začátku, ne jen na oko.

Funkce:
- Dynamický seznam modelů: načítá dostupné modely z Anthropic API /v1/models
- Automatické obnovení: konfigurovatelný interval (výchozí 1 hodina)
- Plynulý fallback: při nedostupnosti API použití cache nebo záložních modelů

Proměnné prostředí:
- ANTHROPIC_API_KEY (povinné): Váš Anthropic API klíč

Nastavení (Valves):
- MODEL_REFRESH_INTERVAL: Interval obnovení seznamu modelů v sekundách (výchozí 3600, 0 = vypnuto)
"""

import os
import json
import logging
import time
from typing import Generator, Union, Dict, Any, List, Optional
from urllib.parse import urlparse
from ipaddress import ip_address, ip_network

import requests
from pydantic import BaseModel, Field
from open_webui.utils.misc import pop_system_message


class Pipe:
    """Jednoduchá integrace Anthropic Claude API."""

    # Bezpečnost: blokování privátních sítí u obrázků z URL (ochrana před SSRF)
    PRIVATE_NETWORKS = [
        ip_network("127.0.0.0/8"),
        ip_network("10.0.0.0/8"),
        ip_network("172.16.0.0/12"),
        ip_network("192.168.0.0/16"),
        ip_network("169.254.0.0/16"),
        ip_network("::1/128"),
        ip_network("fc00::/7"),
    ]

    class Valves(BaseModel):
        """Jednoduchá konfigurace – jen to podstatné."""
        ANTHROPIC_API_KEY: str = Field(
            default="",
            description="Váš Anthropic API klíč"
        )
        MODEL_REFRESH_INTERVAL: int = Field(
            default=3600,
            description="Jak často obnovit seznam modelů z API (sekundy). 0 = vypnout automatické obnovení."
        )

    # Záložní modely při nedostupnosti API
    FALLBACK_MODELS = [
        {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5"},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5"},
        {"id": "claude-opus-4-1-20250805", "name": "Claude Opus 4.1"},
        {"id": "claude-3-7-sonnet-20250219", "name": "Claude 3.7 Sonnet"},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
        {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"},
        {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
    ]

    def __init__(self):
        self.name = "Anthropic Claude"
        self.valves = self.Valves(
            **{"ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "")}
        )
        self.timeout = 60
        self.logger = logging.getLogger(__name__)

        # Cache modelů
        self._cached_models: Optional[List[Dict[str, str]]] = None
        self._cache_timestamp: float = 0

    def pipes(self) -> List[Dict[str, str]]:
        """Vrátí dostupné Claude modely, načtené dynamicky z Anthropic API."""
        if self._is_cache_valid():
            return self._cached_models

        models = self._fetch_models_from_api()

        if models:
            self._cached_models = models
            self._cache_timestamp = time.time()
            return models

        if self._cached_models:
            self.logger.warning("Použití staré cache modelů (API nedostupné)")
            return self._cached_models

        self.logger.warning("Použití záložních modelů (API nedostupné)")
        return self.FALLBACK_MODELS

    def _is_cache_valid(self) -> bool:
        """Zkontroluje, zda je cache modelů ještě platná."""
        if not self._cached_models:
            return False

        refresh_interval = self.valves.MODEL_REFRESH_INTERVAL
        if refresh_interval <= 0:
            return True

        age = time.time() - self._cache_timestamp
        return age < refresh_interval

    def _fetch_models_from_api(self) -> Optional[List[Dict[str, str]]]:
        """Načte dostupné modely z Anthropic API."""
        if not self.valves.ANTHROPIC_API_KEY:
            return None

        try:
            response = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": self.valves.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            models = []
            for model in data.get("data", []):
                model_id = model.get("id", "")
                display_name = model.get("display_name", model_id)

                if not model_id.startswith("claude"):
                    continue

                models.append({
                    "id": model_id,
                    "name": display_name
                })

            if models:
                self.logger.info(f"Načteno {len(models)} modelů z Anthropic API")
                return models

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Načtení modelů z API selhalo: {e}")
        except (KeyError, ValueError) as e:
            self.logger.warning(f"Chyba parsování odpovědi modelů: {e}")

        return None

    def pipe(self, body: Dict[str, Any]) -> Union[str, Generator[str, None, None]]:
        """Zpracuje požadavek a vrátí odpověď Claude."""
        try:
            if not self.valves.ANTHROPIC_API_KEY:
                return "Chyba: ANTHROPIC_API_KEY není nastaven. Přidejte API klíč v nastavení pipeline."

            model_id = self._extract_model_id(body.get("model", ""))

            messages = body.get("messages", [])
            system_message, user_messages = pop_system_message(messages)

            processed_messages = self._process_messages(user_messages)

            payload = {
                "model": model_id,
                "messages": processed_messages,
                "max_tokens": body.get("max_tokens", 4096),
                "stream": body.get("stream", False),
            }

            if system_message:
                payload["system"] = str(system_message)

            for param in ["temperature", "top_p", "top_k"]:
                if param in body:
                    payload[param] = body[param]

            response = self._call_api(payload)

            if body.get("stream", False):
                return self._stream_response(response)
            else:
                return self._parse_response(response)

        except requests.exceptions.RequestException as e:
            error_msg = self._safe_error_message(e)
            self.logger.error(f"API požadavek selhal: {e}")
            return f"Chyba: {error_msg}"

        except ValueError as e:
            self.logger.info(f"Validační chyba: {e}")
            return f"Chyba: {str(e)}"

        except Exception as e:
            self.logger.error(f"Neočekávaná chyba: {type(e).__name__}: {e}", exc_info=True)
            return "Chyba: Něco se pokazilo. Zkuste to znovu."

    def _extract_model_id(self, full_model_id: str) -> str:
        """Z předpony Open WebUI získá čisté ID modelu Claude."""
        if "." in full_model_id:
            return full_model_id.split(".", 1)[-1]
        elif "/" in full_model_id:
            return full_model_id.split("/", 1)[-1]
        return full_model_id

    def _process_messages(self, messages: List[Dict]) -> List[Dict]:
        """Zpracuje zprávy a bezpečně obslouží multimodální obsah (text + obrázky)."""
        processed = []

        for message in messages:
            content = message.get("content", "")

            if isinstance(content, str):
                processed.append({
                    "role": message["role"],
                    "content": content
                })

            elif isinstance(content, list):
                processed_content = []

                for item in content:
                    if item.get("type") == "text":
                        processed_content.append({
                            "type": "text",
                            "text": item.get("text", "")
                        })

                    elif item.get("type") == "image_url":
                        image = self._process_image(item)
                        if image:
                            processed_content.append(image)

                if processed_content:
                    processed.append({
                        "role": message["role"],
                        "content": processed_content
                    })

        return processed

    def _process_image(self, image_data: Dict) -> Dict:
        """Zpracuje obrázek včetně základní bezpečnostní kontroly."""
        url = image_data.get("image_url", {}).get("url", "")

        if url.startswith("data:image"):
            try:
                mime_type, base64_data = url.split(",", 1)
                media_type = mime_type.split(":")[1].split(";")[0]

                size_mb = len(base64_data) * 3 / 4 / (1024 * 1024)
                if size_mb > 5:
                    raise ValueError(f"Obrázek je příliš velký: {size_mb:.1f} MB (max 5 MB)")

                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_data
                    }
                }
            except Exception as e:
                self.logger.warning(f"Zpracování base64 obrázku selhalo: {e}")
                return None

        elif url.startswith("http"):
            if self._is_safe_url(url):
                return {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": url
                    }
                }
            else:
                self.logger.warning(f"Blokováno potenciálně nebezpečné URL: {url}")
                raise ValueError("URL obrázku byla z bezpečnostních důvodů zablokována")

        return None

    def _is_safe_url(self, url: str) -> bool:
        """Ověří URL kvůli ochraně před SSRF útoky."""
        try:
            parsed = urlparse(url)

            if parsed.scheme != "https":
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            blocked_hosts = ["localhost", "metadata.google.internal", "169.254.169.254"]
            if any(blocked in hostname.lower() for blocked in blocked_hosts):
                return False

            try:
                ip = ip_address(hostname)
                for network in self.PRIVATE_NETWORKS:
                    if ip in network:
                        return False
            except ValueError:
                pass

            return True

        except Exception:
            return False

    def _call_api(self, payload: Dict) -> requests.Response:
        """Volá Anthropic API s opakováním při přechodné chybě."""
        headers = {
            "x-api-key": self.valves.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        for attempt in range(3):
            try:
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    stream=payload.get("stream", False)
                )

                if response.status_code in [400, 401, 403]:
                    response.raise_for_status()

                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
                        continue

                response.raise_for_status()
                return response

            except requests.exceptions.Timeout:
                if attempt < 2:
                    continue
                raise

        raise requests.exceptions.RequestException("Překročen maximální počet opakování")

    def _stream_response(self, response: requests.Response) -> Generator[str, None, None]:
        """Streamuje odpověď z Anthropic API."""
        try:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")

                    if line_text.startswith("data: "):
                        data_str = line_text[6:]

                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)

                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")

                            elif data.get("type") == "message_stop":
                                break

                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            self.logger.error(f"Chyba streamování: {e}")
            yield "\n\nChyba: Stream byl přerušen."

    def _parse_response(self, response: requests.Response) -> str:
        """Zpracuje ne-streamovanou odpověď."""
        data = response.json()

        content_blocks = data.get("content", [])
        text_blocks = [
            block.get("text", "")
            for block in content_blocks
            if block.get("type") == "text"
        ]

        return "".join(text_blocks) if text_blocks else "Odpověď nebyla vygenerována."

    def _safe_error_message(self, error: Exception) -> str:
        """Převede výjimku na bezpečnou chybovou zprávu pro uživatele."""
        if isinstance(error, requests.exceptions.Timeout):
            return "Vypršel čas požadavku. Zkuste to znovu."

        if isinstance(error, requests.exceptions.HTTPError):
            status = error.response.status_code
            if status == 401:
                return "Neplatný API klíč. Zkontrolujte ANTHROPIC_API_KEY."
            elif status == 429:
                return "Překročen limit požadavků. Chvíli počkejte."
            elif status >= 500:
                return "Anthropic API je dočasně nedostupné."
            else:
                return "Požadavek na API selhal."

        if isinstance(error, requests.exceptions.ConnectionError):
            return "Nelze se připojit k Anthropic API."

        return "Požadavek selhal. Zkuste to znovu."
