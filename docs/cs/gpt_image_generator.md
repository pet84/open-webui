# GPT Image Generator (Pipe) – česká verze

Pipe od **Chris Bloem** pro generování a úpravu obrázků přes OpenAI (model **gpt-image-1.5**). V chatu se zobrazuje jako model **„GPT Image 1“** – vybereš ho v výběru modelu, napíšeš prompt (nebo přiložíš obrázek a popíšeš úpravu), odešleš a dostaneš obrázek. Nepovídá si, jen generuje/upravuje obrázky.

**Závislosti:** `openai`, `pydantic`, `typing`. Bez dalších knihoven – stahování obrázků z URL používá pouze standardní `urllib`.

**Obrázek z internetu:** Můžeš poslat odkaz na obrázek (např. `https://archenergy.cz/wp-content/uploads/2024/02/rada.jpg`) v textu zprávy – pipe obrázek stáhne a použije pro úpravu. Stejně tak funguje vložený obrázek (data URL) nebo přiložený soubor.

**Rozlišení, rychlost a cena:** Nižší rozlišení = **rychlejší** odpověď a **nižší cena**. V pipe máš **dva „modely“**: **GPT Image 1** (1024×1024, základní) a **GPT Image 1 HD** (vyšší rozlišení). U gpt-image-1.5 je doporučené minimum 1024×1024; 512×512 není podporované a přechod na DALL·E 2 by byl krok zpět.

## Kód (počeštěný + podpora URL + základní/HD)

Pro použití v Open WebUI zkopíruj celý blok níže (od `"""` až po konec třídy). První řádek musí být `"""`.

```python
"""
title: Generátor obrázků GPT (gpt-image-1.5)
description: Rychlý Pipe pro generování a úpravu obrázků pomocí gpt-image-1.5 (včetně obrázků z URL)
author: Chris Bloem (česká verze)
version: 1.6.0
license: MIT
requirements: typing, pydantic, openai
environment_variables:
disclaimer: Použití na vlastní odpovědnost. 1.6.0 Přepnuto na model gpt-image-1.5.
"""

import json
import random
import base64
import asyncio
import re
import tempfile
import os
import logging
import urllib.request
from typing import List, AsyncGenerator, Callable, Awaitable

from pydantic import BaseModel, Field
from openai import OpenAI

# Regex pro detekci obrázků z URL v textu (např. https://example.com/obrazek.jpg)
URL_IMAGE_PATTERN = re.compile(
    r"https?://[^\s<>\"']+\.(?:jpe?g|png|gif|webp)",
    re.IGNORECASE,
)


class Pipe:
    """Pipe: v chatu dva modely – GPT Image 1 (základní) a GPT Image 1 HD."""

    class Valves(BaseModel):
        OPENAI_API_KEYS: str = Field(
            default="", description="OpenAI API klíče, oddělené čárkou"
        )
        IMAGE_NUM: int = Field(default=1, description="Počet obrázků (1–10)")
        IMAGE_SIZE: str = Field(
            default="1024x1024",
            description="Velikost pro GPT Image 1 (základní): 1024x1024, 1536x1024, 1024x1536, auto",
        )
        IMAGE_SIZE_HD: str = Field(
            default="1536x1024",
            description="Velikost pro GPT Image 1 HD (vyšší rozlišení, pomalejší a dražší)",
        )
        IMAGE_QUALITY: str = Field(
            default="auto",
            description="Kvalita: high, medium, low, auto",
        )
        MODERATION: str = Field(
            default="auto",
            description="Moderace: auto (výchozí) nebo low",
        )
        BASE_URL: str = Field(
            default=None,
            description=(
                "Volitelně: Base URL endpointu (např. https://api.openai.com/v1 nebo proxy). "
                "Prázdné = výchozí."
            ),
        )

    def __init__(self):
        self.type = "manifold"
        self.id = "gpt_image_1"
        self.name = "ChatGPT: "
        self.valves = self.Valves()
        self.emitter: Callable[[dict], Awaitable[None]] | None = None

    def _get_base_url(self) -> str | None:
        val = getattr(self.valves, "BASE_URL", None)
        if val is not None and len(val.strip()) > 0:
            return val.strip()
        return None

    async def emit_status(self, message: str = "", done: bool = False):
        if self.emitter:
            await self.emitter(
                {"type": "status", "data": {"description": message, "done": done}}
            )

    def pipes(self) -> List[dict]:
        # Dva modely: základní a HD (1024 minimum u gpt-image-1.5)
        return [
            {"id": "gpt-image-1", "name": "GPT Image 1"},
            {"id": "gpt-image-1-hd", "name": "GPT Image 1 HD"},
        ]

    def convert_message_to_prompt(self, messages: List[dict]) -> tuple[str, List[dict]]:
        """
        Z poslední uživatelské zprávy vytáhne text (prompt) a seznam obrázků.
        Obrázky mohou být: data URL (base64), nebo odkaz na internet (https://...).
        Položky s URL mají tvar {"url": "https://..."} a před voláním API se stáhnou.
        """
        for msg in reversed(messages):
            if msg.get("role") != "user":
                continue

            content = msg.get("content")

            if isinstance(content, list):
                text_parts: List[str] = []
                image_data_list: List[dict] = []

                for part in content:
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            # Vložený obrázek (base64)
                            header, data = url.split(";base64,", 1)
                            mime = header.split("data:")[-1]
                            image_data_list.append({"mimeType": mime, "data": data})
                        elif url.startswith("http://") or url.startswith("https://"):
                            # Odkaz na obrázek z internetu – předáme URL, stáhneme v pipe()
                            image_data_list.append({"url": url})

                prompt = (
                    " ".join(text_parts).strip() or "Uprav přiložený obrázek podle popisu."
                )
                return prompt, image_data_list

            if isinstance(content, str):
                # Obrázky v Markdownu jako data:...;base64,...
                pattern = r"!\[[^\]]*\]\(data:([^;]+);base64,([^)]+)\)"
                matches = re.findall(pattern, content)
                image_data_list = [{"mimeType": m, "data": d} for m, d in matches]
                clean = re.sub(pattern, "", content).strip()

                # V textu hledáme i URL obrázků (např. https://archenergy.cz/.../rada.jpg)
                for match in URL_IMAGE_PATTERN.finditer(clean):
                    image_data_list.append({"url": match.group(0)})
                # Z promptu odstraníme nalezené URL, aby zůstal jen popis úpravy
                clean = URL_IMAGE_PATTERN.sub("", clean).strip()

                prompt = clean or "Uprav přiložený obrázek podle popisu."
                return prompt, image_data_list

        return "Uprav přiložený obrázek podle popisu.", []

    def _get_system_content(self, messages: List[dict]) -> str:
        """Vrátí text systémové zprávy (odkaz, instrukce). Pokud je víc systémových, spojí je."""
        parts = []
        for msg in messages:
            if msg.get("role") != "system":
                continue
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "text" and (part.get("text") or "").strip():
                        parts.append(part.get("text", "").strip())
        return "\n\n".join(parts) if parts else ""

    async def _fetch_url_to_base64(self, url: str) -> dict:
        """Stáhne obrázek z URL a vrátí dict s mimeType a base64 data."""
        def _get() -> dict:
            req = urllib.request.Request(url, headers={"User-Agent": "OpenWebUI-Pipe/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
                if len(data) > 25 * 1024 * 1024:
                    raise ValueError("Obrázek z URL přesahuje limit 25 MB")
                ct = r.headers.get("Content-Type", "image/jpeg")
                mime = ct.split(";")[0].strip().lower()
                if mime not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
                    mime = "image/jpeg"
                return {"mimeType": mime, "data": base64.b64encode(data).decode()}
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _get)

    async def _resolve_images(self, imgs: List[dict]) -> List[dict]:
        """Položky s klíčem 'url' stáhne a převede na mimeType + data."""
        resolved: List[dict] = []
        for img in imgs:
            if "url" in img:
                try:
                    resolved.append(await self._fetch_url_to_base64(img["url"]))
                except Exception as e:
                    raise ValueError(f"Nelze stáhnout obrázek z {img['url']}: {e}")
            else:
                resolved.append(img)
        return resolved

    async def _run_blocking(self, fn: Callable, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    def _pick_api_key(self) -> str | None:
        keys = [k.strip() for k in self.valves.OPENAI_API_KEYS.split(",") if k.strip()]
        if not keys:
            return None
        return random.choice(keys)

    async def generate_image(
        self,
        prompt: str,
        model: str,
        n: int,
        size: str,
        quality: str,
    ) -> AsyncGenerator[str, None]:
        """Volá OpenAI images/generations – nový obrázek z textu."""
        await self.emit_status("🖼️ Generuji...")
        key = self._pick_api_key()
        if not key:
            yield "Chyba: OPENAI_API_KEYS není nastaveno"
            await self.emit_status("❌ Generování obrázku selhalo", done=True)
            return

        client = OpenAI(api_key=key, base_url=self._get_base_url())

        size_arg = None if not size or size.lower() == "auto" else size
        quality_arg = None if not quality or quality.lower() == "auto" else quality

        def _call_gen():
            kwargs = {
                "model": model,
                "prompt": prompt,
                "n": n,
                "moderation": self.valves.MODERATION,
            }
            if size_arg:
                kwargs["size"] = size_arg
            if quality_arg:
                kwargs["quality"] = quality_arg
            return client.images.generate(**kwargs)

        try:
            resp = await self._run_blocking(_call_gen)
            for i, img in enumerate(resp.data, 1):
                yield f"![image_{i}](data:image/png;base64,{img.b64_json})"
            await self.emit_status("🎉 Generování obrázku dokončeno", done=True)
        except Exception as e:
            yield f"Chyba při generování: {e}"
            await self.emit_status("❌ Generování obrázku selhalo", done=True)

    async def edit_image(
        self,
        base64_images: List[dict],
        prompt: str,
        model: str,
        n: int,
        size: str,
        quality: str,
    ) -> AsyncGenerator[str, None]:
        """Volá OpenAI images/edits – úprava přiložených obrázků podle promptu."""
        await self.emit_status("✂️ Upravuji obrázek...")
        key = self._pick_api_key()
        if not key:
            yield "Chyba: OPENAI_API_KEYS není nastaveno"
            await self.emit_status("❌ Úprava obrázku selhala", done=True)
            return

        client = OpenAI(api_key=key, base_url=self._get_base_url())

        images_array = []
        for i, img_dict in enumerate(base64_images, start=1):
            try:
                data = base64.b64decode(img_dict["data"])
                if len(data) > 25 * 1024 * 1024:
                    raise ValueError("Obrázek přesahuje limit 25 MB")

                suffix = {
                    "image/png": ".png",
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/webp": ".webp",
                }.get(img_dict["mimeType"])
                if not suffix:
                    raise ValueError(f"Nepodporovaný formát: {img_dict['mimeType']}")

                image = (f"file{i}{suffix}", data, img_dict["mimeType"])
                images_array.append(image)
            except Exception as e:
                raise ValueError(f"Chyba dekódování obrázku: {e}")

        size_arg = None if not size or size.lower() == "auto" else size
        quality_arg = None if not quality or quality.lower() == "auto" else quality

        def _call_edit(images):
            kwargs = {
                "model": model,
                "image": images,
                "prompt": prompt,
                "n": n,
            }
            if size_arg:
                kwargs["size"] = size_arg

            extra_body = {}
            if quality_arg:
                extra_body["quality"] = quality_arg
            if extra_body:
                kwargs["extra_body"] = extra_body

            return client.images.edit(**kwargs)

        try:
            resp = await self._run_blocking(_call_edit, images_array)
            for i, img in enumerate(resp.data, 1):
                yield f"![image_{i}](data:image/png;base64,{img.b64_json})"
            await self.emit_status("🎉 Úprava obrázku dokončena", done=True)
        except Exception as e:
            yield f"Chyba při úpravě obrázku: {e}"
            await self.emit_status("❌ Úprava obrázku selhala", done=True)

    async def pipe(
        self,
        body: dict,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> AsyncGenerator[str, None]:
        """Hlavní vstup: zprávy z chatu. Pokud jsou obrázky (vložené nebo z URL) → edit, jinak → generování."""
        self.emitter = __event_emitter__
        msgs = body.get("messages", [])

        # Který „model“ uživatel vybral – podle toho zvolíme rozlišení (základní vs HD)
        selected = (body.get("model") or "").strip() or "gpt-image-1"
        if selected == "gpt-image-1-hd":
            size = self.valves.IMAGE_SIZE_HD
        else:
            size = self.valves.IMAGE_SIZE

        model_id = "gpt-image-1.5"
        n = min(max(1, self.valves.IMAGE_NUM), 10)
        quality = self.valves.IMAGE_QUALITY

        prompt, imgs = self.convert_message_to_prompt(msgs)

        # Systémový prompt: pokud v chatu je systémová zpráva (odkaz, instrukce), sloučíme ji s promptem
        # Pak stačí v chatu přidat obrázek a napsat „pracuj“ – úprava proběhne podle systému
        system_content = self._get_system_content(msgs)
        if system_content:
            prompt = (system_content.strip() + "\n\n" + (prompt or "").strip()).strip() or system_content.strip()

        # Obrázky z URL stáhneme a převedeme na base64
        if imgs:
            imgs = await self._resolve_images(imgs)

        if imgs:
            async for out in self.edit_image(
                base64_images=imgs,
                prompt=prompt,
                model=model_id,
                n=n,
                size=size,
                quality=quality,
            ):
                yield out
        else:
            async for out in self.generate_image(
                prompt=prompt,
                model=model_id,
                n=n,
                size=size,
                quality=quality,
            ):
                yield out
```

## Nastavení (Valves)

- **OPENAI_API_KEYS** – jeden nebo více OpenAI API klíčů (oddělené čárkou).
- **IMAGE_NUM** – počet obrázků v jednom běhu (1–10); pro jednu kočičku nech 1.
- **IMAGE_SIZE** – rozlišení pro **GPT Image 1** (základní): `1024x1024`, `1536x1024`, `1024x1536`, `auto`.
- **IMAGE_SIZE_HD** – rozlišení pro **GPT Image 1 HD**: výchozí `1536x1024`. Můžeš změnit na `1024x1536` (na výšku) atd.
- **IMAGE_QUALITY** – `high`, `medium`, `low`, `auto`.
- **MODERATION** – `auto` nebo `low`.
- **BASE_URL** – volitelně, např. `https://api.openai.com/v1` nebo adresa proxy.

## Použití

1. V Open WebUI vyber v chatu jako „model“:
   - **GPT Image 1** – základní 1024×1024 (rychlejší, levnější),
   - **GPT Image 1 HD** – vyšší rozlišení (**IMAGE_SIZE_HD**).
2. Pro **generování**: napiš text (např. „obrázek kočičky“) a odešli.
3. Pro **úpravu**:
   - **Přiložený soubor** – přilož obrázek k zprávě a napiš, co s ním udělat.
   - **Obrázek z internetu** – napiš do zprávy odkaz na obrázek a popis úpravy (pipe URL rozpozná a stáhne).
   - **Systémový prompt + „pracuj“:** V nastavení chatu (nebo v první systémové zprávě) nastav **odkaz / instrukci** – co se má s obrázkem dělat. V chatu pak jen přilož obrázek a napiš **pracuj**. Pipe sloučí systémový text s tvou zprávou a pošle to do API – úprava proběhne podle systému.

Opakované hlášky „Generuji…“ / „Generování obrázku dokončeno“ v jednom běhu bývají tím, že Open WebUI pipe spustí vícekrát; samotný kód s `IMAGE_NUM=1` vrací jeden obrázek na jedno volání.

### Kolikrát se pipe opravdu volá? (log na serveru)

Aby sis ověřil, že za to může víc požadavků z UI, můžeš na **začátek** metody `pipe()` (hned za `self.emitter = __event_emitter__`) dočasně přidat:

```python
import logging
logging.getLogger("open_webui.functions").warning("GPT Image pipe() volání")
```

Pak **restartuj backend** Open WebUI, pošli jednu zprávu (jeden obrázek) a v **logu serveru** (kde běží Open WebUI – konzole, stdout, nebo soubor z dockeru/PM2) hledej řádek `GPT Image pipe() volání`. Kolikrát se objeví za jednu tvoji zprávu, tolikrát se pipe opravdu spustil. Pokud je to víc než 1×, volání posílá frontend nebo middleware (ne náš kód). Log pak můžeš zase odstranit.
