"""
title: Export do Excelu
author: Fu-Jie
author_url: https://github.com/Fu-Jie
funding_url: https://github.com/Fu-Jie/awesome-openwebui
version: 0.3.7
openwebui_id: 244b8f9d-7459-47d6-84d3-c7ae8e3ec710
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xNSAySDZhMiAyIDAgMCAwLTIgMnYxNmEyIDIgMCAwIDAgMiAyaDEyYTIgMiAwIDAgMCAyLTJWN1oiLz48cGF0aCBkPSJNMTQgMnY0YTIgMiAwIDAgMCAyIDJoNCIvPjxwYXRoIGQ9Ik04IDEzaDIiLz48cGF0aCBkPSJNMTQgMTNoMiIvPjxwYXRoIGQ9Ik04IDE3aDIiLz48cGF0aCBkPSJNMTQgMTdoMiIvPjwvc3ZnPg==
description: Extrahuje tabulky ze zpráv chatu a exportuje je do souborů Excel (.xlsx) s inteligentním formátováním.
"""

import os
import pandas as pd
import re
import base64
from fastapi import FastAPI, HTTPException
from typing import Optional, Callable, Awaitable, Any, List, Dict
import datetime
import asyncio
from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.utils.chat import generate_chat_completion
from pydantic import BaseModel, Field
from typing import Literal

app = FastAPI()


class Action:
    class Valves(BaseModel):
        TITLE_SOURCE: Literal["chat_title", "ai_generated", "markdown_title"] = Field(
            default="chat_title",
            description="Zdroj názvu: 'chat_title' (Název chatu), 'ai_generated' (Vygenerovaný AI), 'markdown_title' (Markdown nadpis)",
        )
        EXPORT_SCOPE: Literal["last_message", "all_messages"] = Field(
            default="last_message",
            description="Rozsah exportu: 'last_message' (Pouze poslední zpráva), 'all_messages' (Všechny zprávy)",
        )
        MODEL_ID: str = Field(
            default="",
            description="ID modelu pro generování názvu AI. Ponechte prázdné pro použití aktuálního modelu chatu.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def _send_notification(self, emitter: Callable, type: str, content: str):
        await emitter(
            {"type": "notification", "data": {"type": type, "content": content}}
        )

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__: Optional[Callable[[Any], Awaitable[None]]] = None,
        __request__: Optional[Any] = None,
    ):
        print(f"action:{__name__}")
        if isinstance(__user__, (list, tuple)):
            user_language = (
                __user__[0].get("language", "en-US") if __user__ else "en-US"
            )
            user_name = __user__[0].get("name", "User") if __user__[0] else "User"
            user_id = (
                __user__[0]["id"]
                if __user__ and "id" in __user__[0]
                else "unknown_user"
            )
        elif isinstance(__user__, dict):
            user_language = __user__.get("language", "en-US")
            user_name = __user__.get("name", "User")
            user_id = __user__.get("id", "unknown_user")

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Ukládám do souboru...", "done": False},
                }
            )

            try:
                messages = body.get("messages", [])
                if not messages:
                    raise HTTPException(status_code=400, detail="Nebyly nalezeny žádné zprávy.")

                # Určení zpráv ke zpracování podle rozsahu
                target_messages = []
                if self.valves.EXPORT_SCOPE == "all_messages":
                    target_messages = messages
                else:
                    target_messages = [messages[-1]]

                all_tables = []
                all_sheet_names = []

                # Zpracování zpráv
                for msg_index, msg in enumerate(target_messages):
                    content = msg.get("content", "")
                    tables = self.extract_tables_from_message(content)

                    if not tables:
                        continue

                    # Generování názvů listů pro tabulky této zprávy
                    # Pokud je více zpráv, musíme zajistit unikátnost v celém sešitu
                    # Zde vygenerujeme základní názvy a později je případně deduplikujeme

                    # Extrakce nadpisů pro tuto zprávu
                    headers = []
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if re.match(r"^#{1,6}\s+", line):
                            headers.append(
                                {
                                    "text": re.sub(r"^#{1,6}\s+", "", line).strip(),
                                    "line_num": i,
                                }
                            )

                    for table_index, table in enumerate(tables):
                        sheet_name = ""

                        # 1. Zkusit Markdown nadpis (nejbližší výše)
                        table_start_line = table["start_line"] - 1
                        closest_header_text = None
                        candidate_headers = [
                            h for h in headers if h["line_num"] < table_start_line
                        ]
                        if candidate_headers:
                            closest_header = max(
                                candidate_headers, key=lambda x: x["line_num"]
                            )
                            closest_header_text = closest_header["text"]

                        if closest_header_text:
                            sheet_name = self.clean_sheet_name(closest_header_text)

                        # 2. Vygenerovaný AI (Pouze pokud je explicitně povoleno a máme request objekt)
                        # Poznámka: Generování názvů pro KAŽDOU tabulku ve všech zprávách může být příliš pomalé/nákladné.
                        # Pro 'all_messages' rozsah toto přeskočíme, aby nedošlo k timeoutu, pokud není jen jedna zpráva.
                        if (
                            not sheet_name
                            and self.valves.TITLE_SOURCE == "ai_generated"
                            and len(target_messages) == 1
                        ):
                            # Logika pro AI generování (zjednodušeno, využívá existující tok pokud možno)
                            pass

                        # 3. Záložní: Index zprávy
                        if not sheet_name:
                            if len(target_messages) > 1:
                                # Použít globální index zprávy
                                # Pokud je více tabulek v jedné zprávě: "Zpr 1 - Tab 1"
                                if len(tables) > 1:
                                    sheet_name = f"Zpr{msg_index+1}-Tab{table_index+1}"
                                else:
                                    sheet_name = f"Zpr{msg_index+1}"
                            else:
                                # Jediná zpráva (rozsah last_message)
                                if len(tables) > 1:
                                    sheet_name = f"Tabulka {table_index+1}"
                                else:
                                    sheet_name = "List1"

                        all_tables.append(table)
                        all_sheet_names.append(sheet_name)

                if not all_tables:
                    raise HTTPException(
                        status_code=400, detail="Ve vybraném rozsahu nebyly nalezeny žádné tabulky."
                    )

                # Deduplikace názvů listů
                final_sheet_names = []
                seen_names = {}
                for name in all_sheet_names:
                    base_name = name
                    counter = 1
                    while name in seen_names:
                        name = f"{base_name} ({counter})"
                        counter += 1
                    seen_names[name] = True
                    final_sheet_names.append(name)

                # Oznámení uživateli o počtu nalezených tabulek
                table_count = len(all_tables)
                if self.valves.EXPORT_SCOPE == "all_messages":
                    await self._send_notification(
                        __event_emitter__,
                        "info",
                        f"Nalezeno {table_count} tabulek ve všech zprávách.",
                    )
                    # Počkat chvíli, aby uživatel viděl oznámení před dialogem stahování
                    await asyncio.sleep(1.5)
                # Generování názvu sešitu (název souboru)
                # Použít název chatu nebo první nadpis z první zprávy s tabulkami
                title = ""
                chat_id = self.extract_chat_id(body, None)
                chat_title = ""
                if chat_id:
                    chat_title = await self.fetch_chat_title(chat_id, user_id)

                if (
                    self.valves.TITLE_SOURCE == "chat_title"
                    or not self.valves.TITLE_SOURCE
                ):
                    title = chat_title
                elif self.valves.TITLE_SOURCE == "ai_generated":
                    # Použít AI pro generování názvu na základě obsahu zprávy
                    if target_messages and __request__:
                        # Získat obsah z první zprávy s tabulkami
                        content_for_title = ""
                        for msg in target_messages:
                            msg_content = msg.get("content", "")
                            if msg_content:
                                content_for_title = msg_content
                                break
                        if content_for_title:
                            title = await self.generate_title_using_ai(
                                body,
                                content_for_title,
                                user_id,
                                __request__,
                                __event_emitter__,
                            )
                elif self.valves.TITLE_SOURCE == "markdown_title":
                    # Zkusit najít první nadpis v první zprávě s obsahem
                    for msg in target_messages:
                        extracted = self.extract_title(msg.get("content", ""))
                        if extracted:
                            title = extracted
                            break

                # Záložní název souboru
                if not title:
                    if chat_title:
                        title = chat_title
                    else:
                        # Zkusit extrahovat z obsahu znovu, pokud to ještě nebylo zkušeno
                        if self.valves.TITLE_SOURCE != "markdown_title":
                            for msg in target_messages:
                                extracted = self.extract_title(msg.get("content", ""))
                                if extracted:
                                    title = extracted
                                    break

                current_datetime = datetime.datetime.now()
                formatted_date = current_datetime.strftime("%Y%m%d")

                if not title:
                    workbook_name = f"{user_name}_{formatted_date}"
                else:
                    workbook_name = self.clean_filename(title)

                filename = f"{workbook_name}.xlsx"
                excel_file_path = os.path.join(
                    "app", "backend", "data", "temp", filename
                )

                os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)

                # Uložení tabulek do Excelu
                self.save_tables_to_excel_enhanced(
                    all_tables, excel_file_path, final_sheet_names
                )

                # Spuštění stahování souboru
                if __event_call__:
                    with open(excel_file_path, "rb") as file:
                        file_content = file.read()
                        base64_blob = base64.b64encode(file_content).decode("utf-8")

                    await __event_call__(
                        {
                            "type": "execute",
                            "data": {
                                "code": f"""
                                try {{
                                    const base64Data = "{base64_blob}";
                                    const binaryData = atob(base64Data);
                                    const arrayBuffer = new Uint8Array(binaryData.length);
                                    for (let i = 0; i < binaryData.length; i++) {{
                                        arrayBuffer[i] = binaryData.charCodeAt(i);
                                    }}
                                    const blob = new Blob([arrayBuffer], {{ type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }});
                                    const filename = "{filename}";

                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement("a");
                                    a.style.display = "none";
                                    a.href = url;
                                    a.download = filename;
                                    document.body.appendChild(a);
                                    a.click();
                                    URL.revokeObjectURL(url);
                                    document.body.removeChild(a);
                                }} catch (error) {{
                                    console.error('Chyba při spuštění stahování:', error);
                                }}
                                """
                            },
                        }
                    )
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Soubor uložen", "done": True},
                    }
                )

                # Vyčištění dočasného souboru
                if os.path.exists(excel_file_path):
                    os.remove(excel_file_path)

                return {"message": "Stahování spuštěno"}

            except HTTPException as e:
                print(f"Chyba při zpracování tabulek: {str(e.detail)}")
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Chyba při ukládání souboru: {e.detail}",
                            "done": True,
                        },
                    }
                )
                await self._send_notification(
                    __event_emitter__, "error", "Nebyly nalezeny žádné tabulky k exportu!"
                )
                raise e
            except Exception as e:
                print(f"Chyba při zpracování tabulek: {str(e)}")
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Chyba při ukládání souboru: {str(e)}",
                            "done": True,
                        },
                    }
                )
                await self._send_notification(
                    __event_emitter__, "error", "Nebyly nalezeny žádné tabulky k exportu!"
                )

    async def generate_title_using_ai(
        self,
        body: dict,
        content: str,
        user_id: str,
        request: Any,
        event_emitter: Callable = None,
    ) -> str:
        if not request:
            return ""

        try:
            user_obj = Users.get_user_by_id(user_id)
            # Použít nakonfigurovaný MODEL_ID nebo záložně aktuální model chatu
            model = (
                self.valves.MODEL_ID.strip()
                if self.valves.MODEL_ID
                else body.get("model")
            )

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Jsi užitečný asistent. Vygeneruj krátký, stručný název souboru (max 10 slov) pro Excel export na základě následujícího obsahu. Nepoužívej uvozovky ani přípony souborů. Vyhni se speciálním znakům, které jsou neplatné v názvech souborů. Vypiš pouze název souboru.",
                    },
                    {"role": "user", "content": content[:2000]},  # Omezení délky obsahu
                ],
                "stream": False,
            }

            # Definice úlohy generování
            async def generate_task():
                return await generate_chat_completion(request, payload, user_obj)

            # Definice úlohy oznámení
            async def notification_task():
                # Okamžitě odeslat počáteční oznámení
                if event_emitter:
                    await self._send_notification(
                        event_emitter,
                        "info",
                        "AI generuje název souboru pro váš Excel...",
                    )

                # Následná oznámení každých 5 sekund
                while True:
                    await asyncio.sleep(5)
                    if event_emitter:
                        await self._send_notification(
                            event_emitter,
                            "info",
                            "Stále generuji název, prosím vyčkejte...",
                        )

            # Souběžné spuštění úloh
            gen_future = asyncio.ensure_future(generate_task())
            notify_future = asyncio.ensure_future(notification_task())

            done, pending = await asyncio.wait(
                [gen_future, notify_future], return_when=asyncio.FIRST_COMPLETED
            )

            # Zrušit úlohu oznámení, pokud je generování dokončeno
            if not notify_future.done():
                notify_future.cancel()

            # Získat výsledek
            if gen_future in done:
                response = gen_future.result()
                if response and "choices" in response:
                    return response["choices"][0]["message"]["content"].strip()
            else:
                # Nemělo by se stát, pokud return_when=FIRST_COMPLETED a zrušíme notify
                await gen_future
                response = gen_future.result()
                if response and "choices" in response:
                    return response["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"Chyba při generování názvu: {e}")
            if event_emitter:
                await self._send_notification(
                    event_emitter,
                    "warning",
                    f"Generování názvu AI selhalo, používám výchozí název. Chyba: {str(e)}",
                )

        return ""

    def extract_title(self, content: str) -> str:
        """Extrahuje nadpis pouze z Markdown h1/h2"""
        lines = content.split("\n")
        for line in lines:
            # Hledání pouze h1-h2 nadpisů
            match = re.match(r"^#{1,2}\s+(.+)$", line.strip())
            if match:
                return match.group(1).strip()
        return ""

    def extract_chat_id(self, body: dict, metadata: Optional[dict]) -> str:
        """Extrahuje chat_id z body nebo metadata"""
        if isinstance(body, dict):
            chat_id = body.get("chat_id") or body.get("id")
            if isinstance(chat_id, str) and chat_id.strip():
                return chat_id.strip()

            for key in ("chat", "conversation"):
                nested = body.get(key)
                if isinstance(nested, dict):
                    nested_id = nested.get("id") or nested.get("chat_id")
                    if isinstance(nested_id, str) and nested_id.strip():
                        return nested_id.strip()
        if isinstance(metadata, dict):
            chat_id = metadata.get("chat_id")
            if isinstance(chat_id, str) and chat_id.strip():
                return chat_id.strip()
        return ""

    async def fetch_chat_title(self, chat_id: str, user_id: str = "") -> str:
        """Načte název chatu z databáze podle chat_id"""
        if not chat_id:
            return ""

        def _load_chat():
            if user_id:
                return Chats.get_chat_by_id_and_user_id(id=chat_id, user_id=user_id)
            return Chats.get_chat_by_id(chat_id)

        try:
            chat = await asyncio.to_thread(_load_chat)
        except Exception as exc:
            print(f"Nepodařilo se načíst chat {chat_id}: {exc}")
            return ""

        if not chat:
            return ""

        data = getattr(chat, "chat", {}) or {}
        title = data.get("title") or getattr(chat, "title", "")
        return title.strip() if isinstance(title, str) else ""

    def extract_tables_from_message(self, message: str) -> List[Dict]:
        """
        Extrahuje Markdown tabulky a jejich pozice z textu zprávy
        Vrací strukturu: [{
            "data": data tabulky,
            "start_line": číslo počátečního řádku,
            "end_line": číslo koncového řádku
        }]
        """
        table_row_pattern = r"^\s*\|.*\|.*\s*$"
        rows = message.split("\n")
        tables = []
        current_table = []
        start_line = None
        current_line = 0

        for row in rows:
            current_line += 1
            if re.search(table_row_pattern, row):
                if start_line is None:
                    start_line = current_line  # Zaznamenání počátečního řádku tabulky

                # Zpracování řádku tabulky
                cells = [cell.strip() for cell in row.strip().strip("|").split("|")]

                # Přeskočení oddělovacího řádku
                is_separator_row = all(re.fullmatch(r"[:\-]+", cell) for cell in cells)
                if not is_separator_row:
                    current_table.append(cells)
            elif current_table:
                # Tabulka končí
                tables.append(
                    {
                        "data": current_table,
                        "start_line": start_line,
                        "end_line": current_line - 1,
                    }
                )
                current_table = []
                start_line = None

        # Zpracování poslední tabulky
        if current_table:
            tables.append(
                {
                    "data": current_table,
                    "start_line": start_line,
                    "end_line": current_line,
                }
            )

        return tables

    def generate_names_from_content(self, content: str, tables: List[Dict]) -> tuple:
        """
        Generuje název sešitu a názvů listů na základě obsahu
        - Ignoruje neprázdné odstavce, používá pouze markdown nadpisy (h1-h6).
        - Jedna tabulka: Použije nejbližší nadpis jako název sešitu a listu.
        - Více tabulek: Použije první nadpis v dokumentu jako název sešitu a nejbližší nadpis pro každou tabulku jako název listu.
        - Výchozí pojmenování:
            - Sešit: Řešeno v hlavním toku (uzivatel_rrrrmmdd.xlsx).
            - List: List1, List2, ...
        """
        lines = content.split("\n")
        workbook_name = ""
        sheet_names = []
        all_headers = []

        # 1. Najít všechny h1-h6 nadpisy a jejich pozice
        for i, line in enumerate(lines):
            if re.match(r"^#{1,6}\s+", line):
                all_headers.append(
                    {"text": re.sub(r"^#{1,6}\s+", "", line).strip(), "line_num": i}
                )

        # 2. Vygenerovat název listu pro každou tabulku
        for i, table in enumerate(tables):
            table_start_line = table["start_line"] - 1  # Převést na 0-based index
            closest_header_text = None

            # Najít nejbližší nadpis nad aktuální tabulkou
            candidate_headers = [
                h for h in all_headers if h["line_num"] < table_start_line
            ]
            if candidate_headers:
                # Najít nadpis s největším číslem řádku mezi kandidáty
                closest_header = max(candidate_headers, key=lambda x: x["line_num"])
                closest_header_text = closest_header["text"]

            if closest_header_text:
                # Vyčistit a přidat nalezený nadpis
                sheet_names.append(self.clean_sheet_name(closest_header_text))
            else:
                # Pokud nebyl nalezen žádný nadpis, použít výchozí název "List{i+1}"
                sheet_names.append(f"List{i+1}")

        # 3. Určit název sešitu na základě počtu tabulek
        if len(tables) == 1:
            # Jedna tabulka: Použít její název listu jako název sešitu (pokud není výchozí "List1")
            if sheet_names[0] != "List1":
                workbook_name = sheet_names[0]
        elif len(tables) > 1:
            # Více tabulek: Použít první nadpis v dokumentu jako název sešitu
            if all_headers:
                # Najít nadpis s nejmenším číslem řádku
                first_header = min(all_headers, key=lambda x: x["line_num"])
                workbook_name = first_header["text"]

        # 4. Vyčistit název sešitu (pokud je prázdný, hlavní tok použije výchozí název)
        workbook_name = self.clean_filename(workbook_name) if workbook_name else ""

        return workbook_name, sheet_names

    def clean_filename(self, name: str) -> str:
        """Vyčistí nepovolené znaky v názvu souboru"""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def clean_sheet_name(self, name: str) -> str:
        """Vyčistí název listu (limit 31 znaků, odstranění nepovolených znaků)"""
        name = re.sub(r"[\\/*?[\]:]", "", name).strip()
        return name[:31] if len(name) > 31 else name

    # ======================== Vylepšené formátování ========================

    def calculate_text_width(self, text: str) -> float:
        """
        Vypočítá šířku zobrazení textu s ohledem na CJK znaky
        CJK znaky se počítají jako 2 jednotky, ostatní jako 1 jednotka
        """
        if not text:
            return 0

        width = 0
        for char in str(text):
            # Kontrola, zda je znak CJK
            if "\u4e00" <= char <= "\u9fff" or "\u3000" <= char <= "\u303f":
                width += 2
            else:
                width += 1

        return width

    def calculate_text_height(self, text: str, max_width: int = 50) -> int:
        """
        Vypočítá potřebný počet řádků pro zobrazení textu
        Na základě zalomení řádků a délky textu
        """
        if not text:
            return 1

        text = str(text)
        # Výpočet řádků z explicitních zalomení
        explicit_lines = text.count("\n") + 1

        # Výpočet dodatečných řádků ze zalamování
        text_width = self.calculate_text_width(text.replace("\n", ""))
        wrapped_lines = max(
            1, int(text_width / max_width) + (1 if text_width % max_width > 0 else 0)
        )

        return max(explicit_lines, wrapped_lines)

    def get_column_letter(self, col_index: int) -> str:
        """
        Převede index sloupce na písmeno sloupce Excelu (A, B, C, ..., AA, AB, ...)
        """
        result = ""
        while col_index >= 0:
            result = chr(65 + col_index % 26) + result
            col_index = col_index // 26 - 1
        return result

    def determine_content_type(self, header: str, values: list) -> str:
        """
        Inteligentně určí typ dat na základě záhlaví a obsahu
        Vrací: 'number', 'date', 'sequence', 'text'
        """
        header_lower = str(header).lower().strip()

        # Kontrola klíčových slov v záhlaví
        number_keywords = [
            "množství", "částka", "cena", "náklady", "příjmy", "výdaje", "celkem",
            "mezisoučet", "procento", "%", "poměr", "sazba", "hodnota", "skóre", "body",
            "quantity", "amount", "price", "cost", "revenue", "expense", "total",
            "subtotal", "percentage", "ratio", "rate", "value", "score", "points",
        ]
        date_keywords = ["datum", "čas", "rok", "měsíc", "okamžik", "date", "time", "year", "month", "moment"]
        sequence_keywords = [
            "č", "č.", "id", "index", "pořadí", "řazení", "sekvence", "kód",
            "no", "no.", "rank", "order", "sequence", "code",
        ]

        # Kontrola záhlaví
        for keyword in number_keywords:
            if keyword in header_lower:
                return "number"

        for keyword in date_keywords:
            if keyword in header_lower:
                return "date"

        for keyword in sequence_keywords:
            if keyword in header_lower:
                return "sequence"

        # Kontrola obsahu dat
        if not values:
            return "text"

        sample_values = [
            str(v).strip() for v in values[:10] if str(v).strip()
        ]  # Použít prvních 10 neprázdných hodnot jako vzorek
        if not sample_values:
            return "text"

        numeric_count = 0
        date_count = 0
        sequence_count = 0

        for value in sample_values:
            # Kontrola, zda je číslo
            try:
                float(value.replace(",", "").replace("%", ""))
                numeric_count += 1
                continue
            except ValueError:
                pass

            # Kontrola, zda je formát data
            date_patterns = [
                r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
                r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",
                r"\d{4}\d{2}\d{2}",
            ]
            for pattern in date_patterns:
                if re.match(pattern, value):
                    date_count += 1
                    break

            # Kontrola, zda je formát sekvence
            if (
                re.match(r"^\d+$", value) and len(value) <= 4
            ):  # Pouze číslice a <= 4 znaky, pravděpodobně sekvence
                sequence_count += 1

        total_count = len(sample_values)

        # Určení typu na základě poměru
        if numeric_count / total_count >= 0.7:
            return "number"
        elif date_count / total_count >= 0.7:
            return "date"
        elif sequence_count / total_count >= 0.8 and sequence_count > 2:
            return "sequence"
        else:
            return "text"

    def save_tables_to_excel_enhanced(
        self, tables: List[Dict], file_path: str, sheet_names: List[str]
    ):
        """
        Vylepšená funkce ukládání do Excelu se standardním formátováním
        """
        try:
            with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
                workbook = writer.book

                # Barvy motivu ve stylu OpenWebUI
                HEADER_BG = "#1f2937"  # Tmavě šedá (odpovídá postrannímu panelu OpenWebUI)
                HEADER_FG = "#ffffff"  # Bílý text
                ROW_ODD_BG = "#ffffff"  # Bílá pro liché řádky
                ROW_EVEN_BG = "#f3f4f6"  # Světle šedá pro sudé řádky (zebra pruhování)
                BORDER_COLOR = "#e5e7eb"  # Světlý okraj

                # Definice stylu záhlaví - Zarovnání na střed
                header_format = workbook.add_format(
                    {
                        "bold": True,
                        "font_size": 11,
                        "font_name": "Arial",
                        "font_color": HEADER_FG,
                        "bg_color": HEADER_BG,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "align": "center",
                        "valign": "vcenter",
                        "text_wrap": True,
                    }
                )

                # Styl textové buňky - Zarovnání vlevo (liché řádky)
                text_format = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                    }
                )

                # Styl textové buňky - Zarovnání vlevo (sudé řádky - zebra)
                text_format_alt = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                    }
                )

                # Styl číselné buňky - Zarovnání vpravo
                number_format = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "right",
                        "valign": "vcenter",
                    }
                )

                number_format_alt = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "right",
                        "valign": "vcenter",
                    }
                )

                # Formát celých čísel - Zarovnání vpravo
                integer_format = workbook.add_format(
                    {
                        "num_format": "0",
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "right",
                        "valign": "vcenter",
                    }
                )

                integer_format_alt = workbook.add_format(
                    {
                        "num_format": "0",
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "right",
                        "valign": "vcenter",
                    }
                )

                # Formát desetinných čísel - Zarovnání vpravo
                decimal_format = workbook.add_format(
                    {
                        "num_format": "0.00",
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "right",
                        "valign": "vcenter",
                    }
                )

                decimal_format_alt = workbook.add_format(
                    {
                        "num_format": "0.00",
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "right",
                        "valign": "vcenter",
                    }
                )

                # Formát data - Zarovnání na střed
                date_format = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "center",
                        "valign": "vcenter",
                        "text_wrap": True,
                    }
                )

                date_format_alt = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "center",
                        "valign": "vcenter",
                        "text_wrap": True,
                    }
                )

                # Formát sekvence - Zarovnání na střed
                sequence_format = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "center",
                        "valign": "vcenter",
                    }
                )

                sequence_format_alt = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "center",
                        "valign": "vcenter",
                    }
                )

                # Styl tučné buňky (pro celé buňky s tučným textem)
                text_bold_format = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                        "bold": True,
                    }
                )

                text_bold_format_alt = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                        "bold": True,
                    }
                )

                # Styl kurzívy buňky (pro celé buňky s kurzívou)
                text_italic_format = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_ODD_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                        "italic": True,
                    }
                )

                text_italic_format_alt = workbook.add_format(
                    {
                        "font_name": "Arial",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": ROW_EVEN_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                        "italic": True,
                    }
                )

                # Styl kódu buňky (pro inline kód se zvýrazněným pozadím)
                CODE_BG = "#f0f0f0"  # Světle šedé pozadí pro kód
                text_code_format = workbook.add_format(
                    {
                        "font_name": "Consolas",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": CODE_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                    }
                )

                text_code_format_alt = workbook.add_format(
                    {
                        "font_name": "Consolas",
                        "font_size": 10,
                        "border": 1,
                        "border_color": BORDER_COLOR,
                        "bg_color": CODE_BG,
                        "align": "left",
                        "valign": "vcenter",
                        "text_wrap": True,
                    }
                )

                for i, table in enumerate(tables):
                    try:
                        table_data = table["data"]
                        if not table_data or len(table_data) < 1:
                            print(f"Přeskakuji prázdnou tabulku na indexu {i}")
                            continue

                        print(f"Zpracovávám tabulku {i+1} s {len(table_data)} řádky")

                        # Získání názvu listu
                        sheet_name = (
                            sheet_names[i] if i < len(sheet_names) else f"List{i+1}"
                        )

                        # Vytvoření DataFrame
                        headers = [
                            str(cell).strip()
                            for cell in table_data[0]
                            if str(cell).strip()
                        ]
                        if not headers:
                            print(f"Varování: Pro tabulku {i+1} nebyla nalezena žádná platná záhlaví")
                            headers = [f"Sloup{j+1}" for j in range(len(table_data[0]))]

                        data_rows = []
                        if len(table_data) > 1:
                            max_cols = len(headers)
                            for row in table_data[1:]:
                                processed_row = []
                                for j in range(max_cols):
                                    if j < len(row):
                                        processed_row.append(str(row[j]))
                                    else:
                                        processed_row.append("")
                                data_rows.append(processed_row)
                            df = pd.DataFrame(data_rows, columns=headers)
                        else:
                            df = pd.DataFrame(columns=headers)

                        print(f"DataFrame vytvořen se sloupci: {list(df.columns)}")

                        # Inteligentní konverze datových typů pomocí pandas infer_objects
                        for col in df.columns:
                            # Nejprve zkusit číselnou konverzi
                            try:
                                df[col] = pd.to_numeric(df[col])
                            except (ValueError, TypeError):
                                # Zkusit konverzi data/času
                                try:
                                    df[col] = pd.to_datetime(df[col], errors="raise")
                                except (ValueError, TypeError):
                                    # Ponechat jako string, použít infer_objects pro optimalizaci
                                    df[col] = df[col].infer_objects()

                        # Nejprve zapsat data (bez záhlaví)
                        df.to_excel(
                            writer,
                            sheet_name=sheet_name,
                            index=False,
                            header=False,
                            startrow=1,
                        )
                        worksheet = writer.sheets[sheet_name]

                        # Aplikovat vylepšené formátování se zebra pruhováním
                        formats = {
                            "header": header_format,
                            "text": [text_format, text_format_alt],
                            "number": [number_format, number_format_alt],
                            "integer": [integer_format, integer_format_alt],
                            "decimal": [decimal_format, decimal_format_alt],
                            "date": [date_format, date_format_alt],
                            "sequence": [sequence_format, sequence_format_alt],
                            "bold": [text_bold_format, text_bold_format_alt],
                            "italic": [text_italic_format, text_italic_format_alt],
                            "code": [text_code_format, text_code_format_alt],
                        }
                        self.apply_enhanced_formatting(
                            worksheet,
                            df,
                            headers,
                            workbook,
                            formats,
                        )

                    except Exception as e:
                        print(f"Chyba při zpracování tabulky {i+1}: {str(e)}")
                        continue

        except Exception as e:
            print(f"Chyba při ukládání Excel souboru: {str(e)}")
            raise

    def apply_enhanced_formatting(
        self,
        worksheet,
        df,
        headers,
        workbook,
        formats,
    ):
        """
        Aplikuje vylepšené formátování se zebra pruhováním
        - Záhlaví: Zarovnání na střed (tmavé pozadí)
        - Číslo: Zarovnání vpravo
        - Text: Zarovnání vlevo
        - Datum: Zarovnání na střed
        - Sekvence: Zarovnání na střed
        - Zebra pruhování: střídavé barvy řádků
        - Podporuje Markdown tučné (**text**) a kurzívu (*text*) pro celé buňky
        """
        try:
            # Extrakce formátu ze slovníku formats
            header_format = formats["header"]

            # 1. Zápis záhlaví (Zarovnání na střed) - s odstraněním Markdown značek
            print(f"Zapisuji záhlaví s vylepšeným zarovnáním: {headers}")
            for col_idx, header in enumerate(headers):
                if header and str(header).strip():
                    # Odstranit Markdown značky z názvů sloupců
                    clean_header = str(header).strip()
                    clean_header = re.sub(r"\*\*(.+?)\*\*", r"\1", clean_header)  # **tučné**
                    clean_header = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", clean_header)  # *kurzíva*
                    clean_header = re.sub(r"`(.+?)`", r"\1", clean_header)  # `kód`
                    worksheet.write(0, col_idx, clean_header, header_format)
                else:
                    default_header = f"Sloup{col_idx+1}"
                    worksheet.write(0, col_idx, default_header, header_format)

            # 2. Analýza typů sloupců
            column_types = {}
            for col_idx, column in enumerate(headers):
                if col_idx < len(df.columns):
                    column_values = df.iloc[:, col_idx].tolist()
                    column_types[col_idx] = self.determine_content_type(
                        column, column_values
                    )
                    print(
                        f"Sloupec '{column}' určen jako typ: {column_types[col_idx]}"
                    )
                else:
                    column_types[col_idx] = "text"

            # 3. Zápis a formátování dat se zebra pruhováním
            for row_idx, row in df.iterrows():
                # Určení, zda je lichý nebo sudý řádek (0-indexed, takže řádek 0 je vizuálně lichý jako řádek 1)
                is_alt_row = (
                    row_idx % 2 == 1
                )  # Sudý index = lichý vizuální řádek, použít alternativní formát

                for col_idx, value in enumerate(row):
                    content_type = column_types.get(col_idx, "text")

                    # Výběr formátu na základě typu obsahu a zebra pruhování
                    fmt_idx = 1 if is_alt_row else 0

                    # === MARKDOWN DETEKCE PRO VŠECHNY TYPY ===
                    # Nejprve zkontrolovat Markdown značky (platí pro text i čísla)
                    is_bold = False
                    is_italic = False
                    is_code = False
                    clean_value = value
                    
                    if isinstance(value, str):
                        value_stripped = value.strip()
                        # Kontrola tučného textu (**text**)
                        match_bold = re.fullmatch(r"\*\*(.+)\*\*", value_stripped)
                        # Kontrola kurzívy (*text*)
                        match_italic = re.fullmatch(r"\*([^*]+)\*", value_stripped)
                        # Kontrola kódu (`text`)
                        match_code = re.fullmatch(r"`(.+)`", value_stripped)
                        
                        if match_bold:
                            is_bold = True
                            clean_value = match_bold.group(1)
                        elif match_italic:
                            is_italic = True
                            clean_value = match_italic.group(1)
                        elif match_code:
                            is_code = True
                            clean_value = match_code.group(1)
                        else:
                            # Odstranit částečné markdown značky
                            clean_value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
                            clean_value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", clean_value)
                            clean_value = re.sub(r"`(.+?)`", r"\1", clean_value)

                    # === URČENÍ FORMÁTU ===
                    if content_type == "number":
                        # Číslo - Zarovnání vpravo
                        if pd.api.types.is_numeric_dtype(df.iloc[:, col_idx]):
                            if pd.api.types.is_integer_dtype(df.iloc[:, col_idx]):
                                current_format = formats["integer"][fmt_idx]
                            else:
                                try:
                                    numeric_value = float(clean_value) if isinstance(clean_value, str) else float(value)
                                    if numeric_value.is_integer():
                                        current_format = formats["integer"][fmt_idx]
                                        clean_value = int(numeric_value)
                                    else:
                                        current_format = formats["decimal"][fmt_idx]
                                except (ValueError, TypeError):
                                    current_format = formats["decimal"][fmt_idx]
                        else:
                            current_format = formats["number"][fmt_idx]

                    elif content_type == "date":
                        # Datum - Zarovnání na střed
                        current_format = formats["date"][fmt_idx]

                    elif content_type == "sequence":
                        # Sekvence - Zarovnání na střed
                        current_format = formats["sequence"][fmt_idx]

                    else:
                        # Text - Zarovnání vlevo
                        current_format = formats["text"][fmt_idx]

                    # === PŘEPSÁNÍ FORMÁTU PRO MARKDOWN STYLY ===
                    if is_bold:
                        current_format = formats["bold"][fmt_idx]
                    elif is_italic:
                        current_format = formats["italic"][fmt_idx]
                    elif is_code:
                        current_format = formats["code"][fmt_idx]

                    # === ZÁPIS DO EXCELU ===
                    worksheet.write(row_idx + 1, col_idx, clean_value, current_format)

            # 4. Automatické přizpůsobení šířky sloupců
            for col_idx, column in enumerate(headers):
                col_letter = self.get_column_letter(col_idx)

                # Výpočet šířky záhlaví
                header_width = self.calculate_text_width(str(column))

                # Výpočet maximální šířky dat
                max_data_width = 0
                if not df.empty and col_idx < len(df.columns):
                    for value in df.iloc[:, col_idx]:
                        value_width = self.calculate_text_width(str(value))
                        max_data_width = max(max_data_width, value_width)

                # Základní šířka
                base_width = max(header_width, max_data_width)

                # Úprava šířky podle typu
                content_type = column_types.get(col_idx, "text")
                if content_type == "sequence":
                    optimal_width = max(8, min(15, base_width + 2))
                elif content_type == "number":
                    optimal_width = max(12, min(25, base_width + 3))
                elif content_type == "date":
                    optimal_width = max(15, min(20, base_width + 2))
                else:
                    if base_width <= 10:
                        optimal_width = base_width + 3
                    elif base_width <= 20:
                        optimal_width = base_width + 4
                    else:
                        optimal_width = base_width + 5
                    optimal_width = max(10, min(60, optimal_width))

                worksheet.set_column(f"{col_letter}:{col_letter}", optimal_width)

            # 5. Automatické přizpůsobení výšky řádků
            worksheet.set_row(0, 35)

            for row_idx, row in df.iterrows():
                max_row_height = 20

                for col_idx, value in enumerate(row):
                    if col_idx < len(headers):
                        col_width = min(
                            60,
                            max(
                                10, self.calculate_text_width(str(headers[col_idx])) + 5
                            ),
                        )
                    else:
                        col_width = 15

                    cell_lines = self.calculate_text_height(str(value), col_width)
                    cell_height = cell_lines * 20

                    max_row_height = max(max_row_height, cell_height)

                final_height = min(120, max_row_height)
                worksheet.set_row(row_idx + 1, final_height)

            print(f"Úspěšně aplikováno vylepšené formátování")

        except Exception as e:
            print(f"Varování: Nepodařilo se aplikovat vylepšené formátování: {str(e)}")
            self.apply_basic_formatting_fallback(worksheet, df)

    def apply_basic_formatting_fallback(self, worksheet, df):
        """
        Záložní základní formátování
        """
        try:
            for i, column in enumerate(df.columns):
                column_width = (
                    max(
                        len(str(column)),
                        (df[column].astype(str).map(len).max() if not df.empty else 0),
                    )
                    + 2
                )

                col_letter = self.get_column_letter(i)
                worksheet.set_column(
                    f"{col_letter}:{col_letter}", min(60, max(10, column_width))
                )

        except Exception as e:
            print(f"Chyba v základním formátování: {str(e)}")

        except Exception as e:
            print(f"Chyba v základním formátování: {str(e)}")
