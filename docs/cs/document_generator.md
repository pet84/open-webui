"""
title: Generátor dokumentů (Auto-Fix JSON struktura)
author: Ngo Tan Tai
author_url: https://newnol.io.vn
description: Generuje soubory Word, PowerPoint a Excel. Automaticky nachází data tabulek v komplexních JSON strukturách (sheets, objekty).
required_open_webui_version: 0.4.0
funding_url: https://github.com/newnol
requirements: python-docx, openpyxl, python-pptx, aiohttp
version: 3.3
licence: MIT
"""

import os
import time
import re
import aiohttp
import json
from pydantic import BaseModel, Field

try:
    from docx import Document
    from openpyxl import Workbook
    from pptx import Presentation
except ImportError:
    pass


class Tools:
    class Valves(BaseModel):
        public_domain: str = Field(
            default="https://your-openwebui-domain.com",
            description="Vaše veřejná doména (DŮLEŽITÉ: BEZ koncového lomítka)",
        )
        internal_api_url: str = Field(
            default="http://127.0.0.1:8080",
            description="Interní API URL (Výchozí Docker: http://127.0.0.1:8080)",
        )

    class UserValves(BaseModel):
        openwebui_api_key: str = Field(
            default="",
            description="🔴 POVINNÉ: Vložte sem váš API klíč (Nastavení -> Účet -> API klíče)",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.user_valves = self.UserValves()
        self.file_handler = True

    def _get_api_key(self, __user__: dict) -> str:
        try:
            valves = __user__.get("valves")
            if not valves:
                return ""
            if hasattr(valves, "openwebui_api_key"):
                return valves.openwebui_api_key
            if isinstance(valves, dict):
                return valves.get("openwebui_api_key", "")
            return ""
        except:
            return ""

    # --- HELPER: HLEDÁNÍ DAT TABULKY V CHAOTICKÉM JSON ---
    def _find_table_data(self, data):
        """
        Rekurzivně hledá List of Lists (2D pole) v komplexní JSON struktuře.
        Dobře zpracovává případy: {"sheets": [{"data": [[...]]}]}, {"Sheet1": [[...]]}, atd.
        """
        # Případ 1: Data je List
        if isinstance(data, list):
            if not data:
                return []
            first_item = data[0]

            # 1.1: Pokud je první prvek List -> Toto je standardní datová tabulka [[A,B], [1,2]]
            if isinstance(first_item, list):
                return data

            # 1.2: Pokud je první prvek Dict (Objekt)
            if isinstance(first_item, dict):
                # Pokud má klíč "data" nebo "rows" (běžné ve struktuře sheets) -> Rekurzivně dovnitř
                for key in ["data", "rows", "cells"]:
                    if key in first_item and isinstance(first_item[key], list):
                        return self._find_table_data(first_item[key])

                # Pokud nemá speciální klíč -> Převést List of Dicts na tabulku (klíče jako záhlaví)
                headers = list(first_item.keys())
                rows = [headers]
                for item in data:
                    rows.append([item.get(k, "") for k in headers])
                return rows

        # Případ 2: Data je Dict
        if isinstance(data, dict):
            # Prioritně hledat klíče obsahující data
            for key in ["sheets", "data", "result", "content", "tables"]:
                if key in data:
                    result = self._find_table_data(data[key])
                    if (
                        result
                        and isinstance(result, list)
                        and len(result) > 0
                        and isinstance(result[0], list)
                    ):
                        return result

            # Pokud není známý klíč, zkusit vzít první hodnotu, která je List
            for val in data.values():
                if isinstance(val, (list, dict)):
                    result = self._find_table_data(val)
                    if (
                        result
                        and isinstance(result, list)
                        and len(result) > 0
                        and isinstance(result[0], list)
                    ):
                        return result

        return []

    # --- HELPER: PARSOVÁNÍ SLIDŮ Z PROSTÉHO TEXTU ---
    def _parse_slides_from_text(self, text: str) -> list:
        """
        Parsuje prostý text slidů do strukturovaného formátu.
        Zpracovává formáty jako:
        - "Slide 1: Název\n- odrážka"
        - "### Název slidu\n- obsah"
        """
        slides = []

        # Rozdělit podle "Slide X:" nebo "Slide X " nebo markdown nadpisů
        raw_segments = re.split(
            r"(?:^|\n)(?:Slide\s*\d+[:\s]*|###?\s*)", text, flags=re.IGNORECASE
        )

        for segment in raw_segments:
            if not segment.strip():
                continue

            lines = segment.strip().split("\n")

            # První řádek je Název
            slide_title = lines[0].strip(" :-")

            # Zbývající řádky jsou obsah
            slide_content = "\n".join(lines[1:]).strip()

            # Vyčistit odrážky pro lepší zobrazení
            slide_content = re.sub(
                r"^[-*•]\s*", "• ", slide_content, flags=re.MULTILINE
            )

            if slide_title or slide_content:
                slides.append({"title": slide_title, "content": slide_content})

        return slides

    # --- MARKDOWN PARSER ---
    def _add_markdown_content_to_docx(self, doc, content: str):
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("# "):
                doc.add_heading(line[2:].strip().replace("**", ""), level=1)
            elif line.startswith("## "):
                doc.add_heading(line[3:].strip().replace("**", ""), level=2)
            elif line.startswith("### "):
                doc.add_heading(line[4:].strip().replace("**", ""), level=3)
            else:
                p = (
                    doc.add_paragraph(style="List Bullet")
                    if line.startswith(("- ", "* "))
                    else doc.add_paragraph()
                )
                text = line[2:] if line.startswith(("- ", "* ")) else line
                parts = re.split(r"(\*\*.*?\*\*)", text)
                for part in parts:
                    if part.startswith("**") and part.endswith("**"):
                        p.add_run(part[2:-2]).bold = True
                    else:
                        p.add_run(part)

    # --- UPLOAD HELPER ---
    async def _upload_file(self, local_path: str, filename: str, api_key: str) -> str:
        headers = {"Authorization": f"Bearer {api_key}"}
        base_url = self.valves.internal_api_url.rstrip("/")
        upload_url = f"{base_url}/api/v1/files/"

        try:
            form = aiohttp.FormData()
            form.add_field("file", open(local_path, "rb"), filename=filename)

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            ) as session:
                async with session.post(upload_url, headers=headers, data=form) as resp:
                    status = resp.status
                    text = await resp.text()
                    try:
                        data = await resp.json()
                    except:
                        data = {}

            try:
                os.remove(local_path)
            except:
                pass

            if status < 200 or status >= 300:
                return f"❌ Chyba uploadu {status}: {text}"
            file_id = data.get("id") or data.get("uuid") or data.get("file_id")

            public_base = self.valves.public_domain.rstrip("/")
            download_url = f"{public_base}/api/v1/files/{file_id}/content"

            return f"""
\n\n---
### ✅ Dokument vygenerován!
📁 **Soubor:** `{filename}`
🔗 **Odkaz:** [Klikněte pro stažení]({download_url})
---
"""
        except Exception as e:
            return f"❌ Systémová chyba: {str(e)}"

    # --- HLAVNÍ FUNKCE ---
    async def generate_word_doc(
        self, title: str, content: str, __user__: dict = {}
    ) -> str:
        """
        Vygeneruje Word dokument (.docx) s daným názvem a obsahem.
        Obsah podporuje Markdown formátování (nadpisy, tučné, odrážky).
        """
        api_key = self._get_api_key(__user__)
        if not api_key:
            return "⚠️ Chybí API klíč."
        safe_title = "".join(
            [c for c in title if c.isalnum() or c in (" ", "_")]
        ).rstrip()
        filename = f"{safe_title.replace(' ', '_')}_{int(time.time())}.docx"
        local_path = f"/tmp/{filename}"
        try:
            doc = Document()
            doc.add_heading(title, 0)
            self._add_markdown_content_to_docx(doc, content)
            doc.save(local_path)
            return await self._upload_file(local_path, filename, api_key)
        except Exception as e:
            return f"❌ Chyba Word: {e}"

    async def generate_excel_file(
        self, filename: str, data_json: str, __user__: dict = {}
    ) -> str:
        """
        Vygeneruje Excel soubor (.xlsx).
        Automaticky vyčistí JSON strukturu a najde data tabulky.

        Args:
            filename: Název Excel souboru
            data_json: JSON řetězec obsahující data tabulky (podporuje různé formáty)
        """
        api_key = self._get_api_key(__user__)
        if not api_key:
            return "⚠️ Chybí API klíč."
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"
        local_path = f"/tmp/{int(time.time())}_{filename}"

        try:
            # 1. Parsování JSON
            raw_data = json.loads(data_json)

            # 2. SUPER CHYTRÁ OPRAVA: Rekurzivně najít data tabulky
            final_data = self._find_table_data(raw_data)

            if not final_data:
                return f"❌ Chyba Excel: Nelze najít platná data tabulky v JSON. Přijatá struktura: {str(raw_data)[:100]}..."

            # 3. Zápis do Excelu
            wb = Workbook()
            ws = wb.active
            for row in final_data:
                if isinstance(row, (list, tuple)):
                    ws.append(row)
                else:
                    ws.append([str(row)])

            wb.save(local_path)
            return await self._upload_file(local_path, filename, api_key)
        except Exception as e:
            return f"❌ Chyba Excel: {e}"

    async def generate_pptx_file(
        self, filename: str, title: str, slides_content: str, __user__: dict = {}
    ) -> str:
        """
        Vygeneruje PowerPoint prezentaci (.pptx).

        Args:
            filename: Název PPTX souboru
            title: Hlavní název prezentace
            slides_content: Může být buď:
                - JSON pole: [{"title": "...", "content": "..."}]
                - Prostý text: "Slide 1: Název\n- odrážka\n\nSlide 2: ..."
        """
        api_key = self._get_api_key(__user__)
        if not api_key:
            return "⚠️ Chybí API klíč."
        if not filename.endswith(".pptx"):
            filename += ".pptx"
        local_path = f"/tmp/{int(time.time())}_{filename}"

        try:
            slides = []

            # 1. Nejprve zkusit parsovat JSON
            try:
                slides = json.loads(slides_content)
                # Validace JSON struktury
                if not isinstance(slides, list):
                    raise json.JSONDecodeError("Není list", "", 0)
            except json.JSONDecodeError:
                # 2. Pokud JSON selže, přepnout na manuální parsování textu
                slides = self._parse_slides_from_text(slides_content)

            if not slides:
                return '❌ Chyba PPTX: Ve vstupu nebyly nalezeny žádné platné slidy. Prosím zadejte obsah ve formátu:\n- JSON: [{"title": "...", "content": "..."}]\n- Nebo prostý text: "Slide 1: Název\\n- obsah"'

            # 3. Vytvoření PPTX
            prs = Presentation()

            # Titulní slide
            slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(slide_layout)
            slide.shapes.title.text = title

            # Obsahové slidy
            for item in slides:
                slide_layout = prs.slide_layouts[1]  # Rozložení Název a Obsah
                slide = prs.slides.add_slide(slide_layout)

                # Nastavit Název
                if "title" in item:
                    slide.shapes.title.text = item["title"]

                # Nastavit Obsah
                if "content" in item:
                    try:
                        slide.shapes.placeholders[1].text_frame.text = item["content"]
                    except:
                        pass  # Přeskočit pokud rozložení nemá textový placeholder

            prs.save(local_path)
            return await self._upload_file(local_path, filename, api_key)

        except Exception as e:
            return f"❌ Chyba PPTX: {str(e)}"
