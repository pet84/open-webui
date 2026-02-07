"""
title: Export do Wordu (Vylepšený)
author: Fu-Jie
author_url: https://github.com/Fu-Jie/awesome-openwebui
funding_url: https://github.com/open-webui
version: 0.4.3
openwebui_id: fca6a315-2a45-42cc-8c96-55cbc85f87f2
icon_url: data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9ImN1cnJlbnRDb2xvciIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNiAyMmEyIDIgMCAwIDEtMi0yVjRhMiAyIDAgMCAxIDItMmg4YTIuNCAyLjQgMCAwIDEgMS43MDQuNzA2bDMuNTg4IDMuNTg4QTIuNCAyLjQgMCAwIDEgMjAgOHYxMmEyIDIgMCAwIDEtMiAyeiIgLz4KICA8cGF0aCBkPSJNMTQgMnY1YTEgMSAwIDAgMCAxIDFoNSIgLz4KICA8cGF0aCBkPSJNMTAgOUg4IiAvPgogIDxwYXRoIGQ9Ik0xNiAxM0g4IiAvPgogIDxwYXRoIGQ9Ik0xNiAxN0g4IiAvPgo8L3N2Zz4K
requirements: python-docx, Pygments, latex2mathml, mathml2omml
description: Export aktuální konverzace z Markdown do Wordu (.docx) s Mermaid diagramy renderovanými na straně klienta (Mermaid.js, SVG+PNG), LaTeX matematikou, skutečnými hypertextovými odkazy, vylepšenými tabulkami, zvýrazněním syntaxe a podporou citací.
notes: Vylepšená verze založená na forku rbb-dev (https://github.com/rbb-dev/awesome-openwebui). Přidána i18n podpora, konfigurovatelné fonty/barvy a optimalizace paralelního PNG renderování.

⚠️ POZNÁMKA: Tento soubor je rozdělen na části pro postupné doplnění.
Kód je zkrácený - chybí implementace mnoha metod (označeno TODO komentáři).
Pro kompletní kód:
1. Jdi do Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
2. Zkopíruj celý kód (Ctrl+A, Ctrl+C)
3. Vlož sem (Ctrl+V) - nahraď celý obsah od řádku 1129 až do konce
Nebo použij: https://github.com/Fu-Jie/awesome-openwebui
"""

from __future__ import annotations

import re
import base64
import datetime
import time
import io
import asyncio
import logging
import hashlib
import struct
import zlib
import binascii
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, Any, List, Tuple, Dict, cast
from urllib.parse import quote
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import parse_xml
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement
from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.utils.chat import generate_chat_completion
from pydantic import BaseModel, Field

# Files slouží k vkládání interních obrázků /api/v1/files/<id>/content.
try:
    from open_webui.models.files import Files  # type: ignore
except Exception:  # pragma: no cover - závisí na hostitelském Open WebUI runtime
    Files = None

# Pygments pro zvýraznění syntaxe
try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.token import Token

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

try:
    from latex2mathml.converter import convert as latex_to_mathml
    import mathml2omml

    LATEX_MATH_AVAILABLE = True
except Exception:
    LATEX_MATH_AVAILABLE = False

# boto3 pro přímý přístup k S3 (rychlejší než API fallback)
try:
    import boto3
    from botocore.config import Config as BotoConfig
    import os

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_AUTO_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>()]+")
_DATA_IMAGE_URL_RE = re.compile(
    r"^data:(?P<mime>image/[a-z0-9.+-]+)\s*;\s*base64\s*,\s*(?P<b64>.*)$",
    re.IGNORECASE | re.DOTALL,
)
_OWUI_API_FILE_ID_RE = re.compile(
    r"/api/v1/files/(?P<id>[A-Za-z0-9-]+)(?:/content)?(?:[/?#]|$)",
    re.IGNORECASE,
)
_CURRENCY_NUMBER_RE = re.compile(r"^\d[\d,]*(?:\.\d+)?$")

_TRANSPARENT_1PX_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQImWNgYGBgAAAABQABDQottAAAAABJRU5ErkJggg=="
)

_ASVG_NS = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
nsmap.setdefault("asvg", _ASVG_NS)

_REASONING_DETAILS_RE = re.compile(
    r"<details\b[^>]*\btype\s*=\s*(?:\"reasoning\"|'reasoning'|reasoning)[^>]*>.*?</details\s*>",
    re.IGNORECASE | re.DOTALL,
)
_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think\s*>", re.IGNORECASE | re.DOTALL)
_ANALYSIS_RE = re.compile(
    r"<analysis\b[^>]*>.*?</analysis\s*>", re.IGNORECASE | re.DOTALL
)


@dataclass(frozen=True)
class _CitationRef:
    idx: int
    anchor: str
    title: str
    url: Optional[str]
    source_id: str


class Action:
    # Slovníky internacionalizovaných zpráv
    _I18N_MESSAGES: Dict[str, Dict[str, str]] = {
        "en": {
            "converting": "Converting to Word document...",
            "exported": "Word document exported",
            "success": "Successfully exported to {filename}",
            "error_no_content": "No content found to export!",
            "error_export": "Error exporting Word document: {error}",
            "export_failed": "Export failed: {error}",
            "figure_prefix": "Figure",
            "references": "References",
        },
        "zh": {
            "converting": "正在转换为 Word 文档...",
            "exported": "Word 文档导出完成",
            "success": "成功导出至 {filename}",
            "error_no_content": "没有找到可导出的内容！",
            "error_export": "导出 Word 文档时出错: {error}",
            "export_failed": "导出失败: {error}",
            "figure_prefix": "图",
            "references": "参考文献",
        },
        "cs": {
            "converting": "Převádím do Word dokumentu...",
            "exported": "Word dokument exportován",
            "success": "Úspěšně exportováno do {filename}",
            "error_no_content": "Nebyl nalezen žádný obsah k exportu!",
            "error_export": "Chyba při exportu Word dokumentu: {error}",
            "export_failed": "Export selhal: {error}",
            "figure_prefix": "Obrázek",
            "references": "Reference",
        },
    }

    class Valves(BaseModel):
        TITLE_SOURCE: str = Field(
            default="chat_title",
            description="Zdroj názvu: 'chat_title' (Název chatu), 'ai_generated' (Vygenerovaný AI), 'markdown_title' (Markdown nadpis)",
        )
        SHOW_STATUS: bool = Field(
            default=True,
            description="Zda zobrazovat aktualizace stavu operace.",
        )
        SHOW_DEBUG_LOG: bool = Field(
            default=False,
            description="Zda vypisovat ladící logy do konzole prohlížeče.",
        )

        MAX_EMBED_IMAGE_MB: int = Field(
            default=20,
            description="Maximální velikost obrázku pro vložení do DOCX (MB). Platí pro data URL a obrázky /api/v1/files/<id>/content.",
        )

        # Konfigurace písem
        FONT_LATIN: str = Field(
            default="Times New Roman",
            description="Písmo pro latinské znaky (např. 'Times New Roman', 'Calibri', 'Arial')",
        )
        FONT_ASIAN: str = Field(
            default="SimSun",
            description="Písmo pro asijské znaky (např. 'SimSun', 'Microsoft YaHei', 'PingFang SC')",
        )
        FONT_CODE: str = Field(
            default="Consolas",
            description="Písmo pro bloky kódu a inline kód (např. 'Consolas', 'Courier New', 'Monaco')",
        )

        # Stylování tabulek
        TABLE_HEADER_COLOR: str = Field(
            default="F2F2F2",
            description="Barva pozadí záhlaví tabulky (hex, bez #)",
        )
        TABLE_ZEBRA_COLOR: str = Field(
            default="FBFBFB",
            description="Barva zebra pruhování pro střídavé řádky tabulky (hex, bez #)",
        )

        MERMAID_JS_URL: str = Field(
            default="https://cdn.jsdelivr.net/npm/mermaid@11.12.2/dist/mermaid.min.js",
            description="URL CDN Mermaid JS",
        )
        MERMAID_JSZIP_URL: str = Field(
            default="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js",
            description="URL CDN JSZip (manipulace DOCX)",
        )
        MERMAID_PNG_SCALE: float = Field(
            default=3.0,
            description="Násobitel rozlišení PNG renderování (vyšší = ostřejší, větší soubor)",
        )
        MERMAID_DISPLAY_SCALE: float = Field(
            default=1.0,
            description="Šířka diagramu relativně k dostupné šířce stránky (doporučeno <=1)",
        )
        MERMAID_OPTIMIZE_LAYOUT: bool = Field(
            default=False,
            description="Optimalizovat Mermaid rozložení: převést LR na TD pro graph/flowchart",
        )
        MERMAID_BACKGROUND: str = Field(
            default="",
            description="Barva pozadí Mermaid. Prázdné = průhledné (doporučeno pro tmavý režim Wordu). Používá se pouze pro volitelné PNG vyplnění.",
        )

        MERMAID_CAPTIONS_ENABLE: bool = Field(
            default=True,
            description="Přidat popisky obrázků pod Mermaid obrázky/grafy",
        )
        MERMAID_CAPTION_STYLE: str = Field(
            default="Caption",
            description="Název stylu odstavce pro Mermaid popisky (používá 'Caption' pokud je k dispozici, jinak vytvoří bezpečný vlastní styl)",
        )
        MERMAID_CAPTION_PREFIX: str = Field(
            default="",
            description="Předpona popisku (např. 'Obrázek' nebo '图'). Prázdné = automatická detekce podle jazyka uživatele.",
        )

        MATH_ENABLE: bool = Field(
            default=True,
            description="Povolit konverzi LaTeX matematických bloků (\\[...\\] a $$...$$) na Word rovnice",
        )
        MATH_INLINE_DOLLAR_ENABLE: bool = Field(
            default=True,
            description="Povolit konverzi inline $...$ matematiky na Word rovnice (konzervativní parsování pro snížení falešných pozitiv)",
        )

        # Konfigurace jazyka
        UI_LANGUAGE: str = Field(
            default="cs",
            description="Jazyk UI pro exportní zprávy. Možnosti: 'en' (Angličtina), 'zh' (Čínština), 'cs' (Čeština)",
        )

    class UserValves(BaseModel):
        TITLE_SOURCE: str = Field(
            default="chat_title",
            description="Zdroj názvu: 'chat_title' (Název chatu), 'ai_generated' (Vygenerovaný AI), 'markdown_title' (Markdown nadpis)",
        )
        UI_LANGUAGE: str = Field(
            default="cs",
            description="Jazyk UI pro exportní zprávy. Možnosti: 'en' (Angličtina), 'zh' (Čínština), 'cs' (Čeština)",
        )
        FONT_LATIN: str = Field(
            default="Times New Roman",
            description="Písmo pro latinské znaky (např. 'Times New Roman', 'Calibri', 'Arial')",
        )
        FONT_ASIAN: str = Field(
            default="SimSun",
            description="Písmo pro asijské znaky (např. 'SimSun', 'Microsoft YaHei', 'PingFang SC')",
        )
        FONT_CODE: str = Field(
            default="Consolas",
            description="Písmo pro bloky kódu a inline kód (např. 'Consolas', 'Courier New', 'Monaco')",
        )
        TABLE_HEADER_COLOR: str = Field(
            default="F2F2F2",
            description="Barva pozadí záhlaví tabulky (hex, bez #)",
        )
        TABLE_ZEBRA_COLOR: str = Field(
            default="FBFBFB",
            description="Barva zebra pruhování pro střídavé řádky tabulky (hex, bez #)",
        )
        MERMAID_PNG_SCALE: float = Field(
            default=3.0,
            description="Násobitel rozlišení PNG renderování (vyšší = ostřejší, větší soubor)",
        )
        MERMAID_DISPLAY_SCALE: float = Field(
            default=1.0,
            description="Šířka diagramu relativně k dostupné šířce stránky (doporučeno <=1)",
        )
        MERMAID_OPTIMIZE_LAYOUT: bool = Field(
            default=False,
            description="Optimalizovat Mermaid rozložení: převést LR na TD pro graph/flowchart",
        )
        MERMAID_BACKGROUND: str = Field(
            default="",
            description="Barva pozadí Mermaid. Prázdné = průhledné (doporučeno pro tmavý režim Wordu). Používá se pouze pro volitelné PNG vyplnění.",
        )
        MERMAID_CAPTIONS_ENABLE: bool = Field(
            default=True,
            description="Přidat popisky obrázků pod Mermaid obrázky/grafy",
        )
        MATH_ENABLE: bool = Field(
            default=True,
            description="Povolit konverzi LaTeX matematických bloků (\\\\[...\\\\] a $$...$$) na Word rovnice",
        )
        MATH_INLINE_DOLLAR_ENABLE: bool = Field(
            default=True,
            description="Povolit konverzi inline $...$ matematiky na Word rovnice (konzervativní parsování pro snížení falešných pozitiv)",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._mermaid_figure_counter: int = 0
        self._mermaid_placeholder_counter: int = 0
        self._caption_style_name: Optional[str] = None
        self._citation_anchor_by_index: Dict[int, str] = {}
        self._citation_refs: List[_CitationRef] = []
        self._bookmark_id_counter: int = 1
        self._active_doc: Optional[Document] = None
        self._user_lang: str = "cs"  # Bude nastaveno per-request
        self._api_token: Optional[str] = None
        self._api_base_url: Optional[str] = None

    def _get_lang_key(self, user_language: str) -> str:
        """Převede kód jazyka uživatele na i18n klíč (např. 'zh-CN' -> 'zh', 'cs-CZ' -> 'cs', 'en-US' -> 'en')."""
        lang = (user_language or "cs").lower().split("-")[0]
        return lang if lang in self._I18N_MESSAGES else "en"

    def _get_msg(self, key: str, **kwargs) -> str:
        """Získá internacionalizovanou zprávu podle klíče s volitelným formátováním."""
        messages = self._I18N_MESSAGES.get(self._user_lang, self._I18N_MESSAGES["en"])
        msg = messages.get(key, self._I18N_MESSAGES["en"].get(key, key))
        if kwargs:
            try:
                return msg.format(**kwargs)
            except KeyError:
                return msg
        return msg

    def _get_user_context(self, __user__: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Bezpečně extrahuje kontextové informace o uživateli."""
        if isinstance(__user__, (list, tuple)):
            user_data = __user__[0] if __user__ else {}
        elif isinstance(__user__, dict):
            user_data = __user__
        else:
            user_data = {}

        return {
            "user_id": user_data.get("id", "unknown_user"),
            "user_name": user_data.get("name", "User"),
            "user_language": user_data.get("language", "cs-CZ"),
        }

    def _get_chat_context(
        self, body: dict, __metadata__: Optional[dict] = None
    ) -> Dict[str, str]:
        """
        Jednotná extrakce kontextových informací chatu (chat_id, message_id).
        Prioritně extrahuje z body, pak z metadata.
        """
        chat_id = ""
        message_id = ""

        # 1. Zkusit získat z body
        if isinstance(body, dict):
            chat_id = body.get("chat_id", "")
            message_id = body.get("id", "")  # message_id je obvykle 'id' v body

            # Zkontrolovat body.metadata jako fallback
            if not chat_id or not message_id:
                body_metadata = body.get("metadata", {})
                if isinstance(body_metadata, dict):
                    if not chat_id:
                        chat_id = body_metadata.get("chat_id", "")
                    if not message_id:
                        message_id = body_metadata.get("message_id", "")

        # 2. Zkusit získat z __metadata__ (jako doplnění)
        if __metadata__ and isinstance(__metadata__, dict):
            if not chat_id:
                chat_id = __metadata__.get("chat_id", "")
            if not message_id:
                message_id = __metadata__.get("message_id", "")

        return {
            "chat_id": str(chat_id).strip(),
            "message_id": str(message_id).strip(),
        }

    async def _emit_status(
        self,
        emitter: Optional[Callable[[Any], Awaitable[None]]],
        description: str,
        done: bool = False,
    ):
        """Vysílá událost aktualizace stavu."""
        if self.valves.SHOW_STATUS and emitter:
            await emitter(
                {"type": "status", "data": {"description": description, "done": done}}
            )

    async def _emit_notification(
        self,
        emitter: Optional[Callable[[Any], Awaitable[None]]],
        content: str,
        ntype: str = "info",
    ):
        """Vysílá událost oznámení (info, success, warning, error)."""
        if emitter:
            await emitter(
                {"type": "notification", "data": {"type": ntype, "content": content}}
            )

    async def _emit_debug_log(self, emitter, title: str, data: dict):
        """Vypíše strukturované ladící logy do konzole prohlížeče"""
        if not self.valves.SHOW_DEBUG_LOG or not emitter:
            return

        try:
            import json

            js_code = f"""
                (async function() {{
                    console.group("🛠️ {title}");
                    console.log({json.dumps(data, ensure_ascii=False)});
                    console.groupEnd();
                }})();
            """

            await emitter({"type": "execute", "data": {"code": js_code}})
        except Exception as e:
            print(f"Chyba při vysílání ladícího logu: {e}")

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__: Optional[Callable[[Any], Awaitable[None]]] = None,
        __metadata__: Optional[dict] = None,
        __request__: Optional[Any] = None,
    ):
        logger.info(f"action:{__name__}")

        # Parsování informací o uživateli
        user_name = "User"
        user_id = "unknown_user"
        if isinstance(__user__, (list, tuple)):
            user_name = __user__[0].get("name", "User") if __user__[0] else "User"
            user_id = (
                __user__[0]["id"]
                if __user__ and "id" in __user__[0]
                else "unknown_user"
            )
        elif isinstance(__user__, dict):
            user_name = __user__.get("name", "User")
            user_id = __user__.get("id", "unknown_user")

        # Aplikovat UserValves pokud jsou přítomné
        if __user__ and "valves" in __user__:
            for key, value in __user__["valves"].model_dump().items():
                if hasattr(self.valves, key):
                    setattr(self.valves, key, value)

        # Získat jazyk uživatele z konfigurace Valves
        self._user_lang = self._get_lang_key(self.valves.UI_LANGUAGE)

        # Extrahovat API connection info pro načítání souborů (podpora S3/Object Storage)
        def _get_default_base_url() -> str:
            port = os.environ.get("PORT") or "8080"
            return f"http://localhost:{port}"

        if __request__:
            try:
                self._api_token = __request__.headers.get("Authorization")
                self._api_base_url = str(__request__.base_url).rstrip("/")
            except Exception:
                self._api_token = None
                self._api_base_url = _get_default_base_url()
        else:
            self._api_token = None
            self._api_base_url = _get_default_base_url()

        if __event_emitter__:
            last_assistant_message = body["messages"][-1]

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": self._get_msg("converting"),
                        "done": False,
                    },
                }
            )

            try:
                message_content = last_assistant_message["content"]
                if isinstance(message_content, str):
                    message_content = self._strip_reasoning_blocks(message_content)

                if not message_content or not message_content.strip():
                    await self._emit_notification(
                        __event_emitter__, self._get_msg("error_no_content"), "error"
                    )
                    return

                # Generování názvu souboru
                title = ""
                chat_ctx = self._get_chat_context(body, __metadata__)
                chat_id = chat_ctx["chat_id"]

                # Načíst chat_title přímo přes chat_id, protože obvykle chybí v body
                chat_title = ""
                if chat_id:
                    chat_title = await self.fetch_chat_title(chat_id, user_id)

                if (
                    self.valves.TITLE_SOURCE.strip() == "chat_title"
                    or not self.valves.TITLE_SOURCE.strip()
                ):
                    title = chat_title
                elif self.valves.TITLE_SOURCE.strip() == "markdown_title":
                    title = self.extract_title(message_content)
                elif self.valves.TITLE_SOURCE.strip() == "ai_generated":
                    title = await self.generate_title_using_ai(
                        body, message_content, user_id, __request__
                    )

                # Záložní logika
                if not title:
                    if self.valves.TITLE_SOURCE.strip() != "chat_title" and chat_title:
                        title = chat_title
                    elif self.valves.TITLE_SOURCE.strip() != "markdown_title":
                        extracted = self.extract_title(message_content)
                        if extracted:
                            title = extracted

                current_datetime = datetime.datetime.now()
                formatted_date = current_datetime.strftime("%Y%m%d")

                cleaned_title = self.clean_filename(title) if title else ""
                if cleaned_title:
                    filename = f"{cleaned_title}.docx"
                else:
                    clean_user = self.clean_filename(user_name)
                    filename = f"{clean_user}_{formatted_date}.docx"

                # Escape názvu souboru pro JS string
                js_filename = filename.replace("\\", "\\\\").replace('"', '\\"')

                top_heading = ""
                if chat_title:
                    top_heading = chat_title
                elif title:
                    top_heading = title

                # Vytvořit Word dokument; pokud neexistuje h1, vložit název chatu jako h1
                has_h1 = bool(re.search(r"^#\s+.+$", message_content, re.MULTILINE))
                sources = (
                    last_assistant_message.get("sources") or body.get("sources") or []
                )
                doc = await self.markdown_to_docx(
                    message_content,
                    top_heading=top_heading,
                    has_h1=has_h1,
                    sources=sources,
                    event_emitter=__event_emitter__,
                )

                # Uložit do paměti
                doc_buffer = io.BytesIO()
                doc.save(doc_buffer)
                doc_buffer.seek(0)
                file_content = doc_buffer.read()
                base64_blob = base64.b64encode(file_content).decode("utf-8")

                # Spustit stahování souboru
                if __event_call__:
                    await __event_call__(
                        {
                            "type": "execute",
                            "data": {
                                "code": f"""
                                (async function() {{
                                    const base64Data = "{base64_blob}";
                                    const filename = "{js_filename}";
	                                    const mermaidUrl = "{self.valves.MERMAID_JS_URL}";
	                                    const jszipUrl = "{self.valves.MERMAID_JSZIP_URL}";
	                                    const pngScale = {float(self.valves.MERMAID_PNG_SCALE)};
	                                    const displayScale = {float(self.valves.MERMAID_DISPLAY_SCALE)};
	                                    const bgRaw = "{(self.valves.MERMAID_BACKGROUND or '').strip()}";
	                                    const bg = (bgRaw || "").trim();
	                                    const bgFill = (bg && bg.toLowerCase() !== "transparent") ? bg : "";
	                                    const themeBackground = bgFill || "transparent";

                                    function downloadBlob(blob, filename) {{
                                        const url = URL.createObjectURL(blob);
                                        const a = document.createElement("a");
                                        a.style.display = "none";
                                        a.href = url;
                                        a.download = filename;
                                        document.body.appendChild(a);
                                        a.click();
                                        URL.revokeObjectURL(url);
                                        document.body.removeChild(a);
                                    }}

                                    async function loadScript(url, globalName) {{
                                        if (globalName && window[globalName]) return;
                                        await new Promise((resolve, reject) => {{
                                            const script = document.createElement("script");
                                            script.src = url;
                                            script.onload = resolve;
                                            script.onerror = reject;
                                            document.head.appendChild(script);
                                        }});
                                    }}

                                    function decodeBase64ToUint8Array(b64) {{
                                        const binary = atob(b64);
                                        const bytes = new Uint8Array(binary.length);
                                        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                                        return bytes;
                                    }}

                                    function parseViewBox(vb) {{
                                        if (!vb) return null;
                                        const parts = vb.trim().split(/\\s+/).map(Number);
                                        if (parts.length !== 4 || parts.some((n) => !isFinite(n))) return null;
                                        return {{ minX: parts[0], minY: parts[1], width: parts[2], height: parts[3] }};
                                    }}

	                                    function normalizeSvgForWord(svgText) {{
	                                        const parser = new DOMParser();
	                                        const doc = parser.parseFromString(svgText, "image/svg+xml");
	                                        const svgEl = doc.documentElement;
	                                        if (!svgEl || svgEl.tagName.toLowerCase() !== "svg") return svgText;

                                        const vb0 = parseViewBox(svgEl.getAttribute("viewBox"));
                                        if (vb0 && vb0.width > 0 && vb0.height > 0) {{
                                            const minDim = Math.min(vb0.width, vb0.height);
                                            let pad = Math.max(8.0, minDim * 0.02);
                                            pad = Math.min(pad, 24.0);
                                            const vb = {{
                                                minX: vb0.minX - pad,
                                                minY: vb0.minY - pad,
                                                width: vb0.width + 2 * pad,
                                                height: vb0.height + 2 * pad,
                                            }};
                                            svgEl.setAttribute("viewBox", `${{vb.minX}} ${{vb.minY}} ${{vb.width}} ${{vb.height}}`);
                                        }}

                                        const vb = parseViewBox(svgEl.getAttribute("viewBox"));
                                        const widthAttr = (svgEl.getAttribute("width") || "").trim();
                                        const heightAttr = (svgEl.getAttribute("height") || "").trim();
                                        const widthPct = widthAttr.endsWith("%");
                                        const heightPct = heightAttr.endsWith("%");
                                        if (vb && vb.width > 0 && vb.height > 0 && (!widthAttr || !heightAttr || widthPct || heightPct)) {{
                                            svgEl.setAttribute("width", `${{vb.width}}`);
                                            svgEl.setAttribute("height", `${{vb.height}}`);
                                        }}

	                                        svgEl.removeAttribute("style");
	                                        svgEl.setAttribute("preserveAspectRatio", "xMidYMid meet");
		                                        svgEl.setAttribute("overflow", "visible");

		                                        const removeNode = (n) => {{
		                                            try {{ n && n.parentNode && n.parentNode.removeChild(n); }} catch (_e) {{}}
		                                        }};

		                                        svgEl
		                                            .querySelectorAll('rect[data-owui-bg=\"1\"], rect.background, rect[class~=\"background\"], rect#background')
		                                            .forEach(removeNode);
		                                        try {{
		                                            const isWhiteish = (fill) => {{
		                                                const f = (fill || "").trim().toLowerCase();
	                                                return (
	                                                    f === "white" ||
	                                                    f === "#fff" ||
	                                                    f === "#ffffff" ||
	                                                    f === "rgb(255,255,255)" ||
	                                                    f === "rgb(255, 255, 255)"
	                                                );
	                                            }};
	                                            const nearly = (a, b) => Math.abs(a - b) <= 1e-3;
	                                            const rectMatches = (r, box) => {{
	                                                if (!box) return false;
	                                                const x = parseFloat(r.getAttribute("x") || "0");
	                                                const y = parseFloat(r.getAttribute("y") || "0");
	                                                const w = parseFloat(r.getAttribute("width") || "");
	                                                const h = parseFloat(r.getAttribute("height") || "");
	                                                if (!isFinite(x) || !isFinite(y) || !isFinite(w) || !isFinite(h)) return false;
	                                                return (
	                                                    nearly(x, box.minX) &&
	                                                    nearly(y, box.minY) &&
	                                                    nearly(w, box.width) &&
	                                                    nearly(h, box.height)
	                                                );
		                                            }};
		                                            const vbNow = parseViewBox(svgEl.getAttribute("viewBox"));
		                                            svgEl.querySelectorAll("rect[fill]").forEach((r) => {{
		                                                const fill = r.getAttribute("fill");
		                                                if (!isWhiteish(fill)) return;
		                                                if (rectMatches(r, vb0) || rectMatches(r, vbNow)) removeNode(r);
		                                            }});
		                                        }} catch (_e) {{}}
		                                        try {{
		                                            const vbCanvas = parseViewBox(svgEl.getAttribute(\"viewBox\")) || vb0 || vb;
		                                            if (vbCanvas) {{
		                                                const existing = svgEl.querySelector('rect[data-owui-canvas=\"1\"]');
		                                                const rect = existing || doc.createElementNS(\"http://www.w3.org/2000/svg\", \"rect\");
		                                                rect.setAttribute(\"data-owui-canvas\", \"1\");
		                                                rect.setAttribute(\"x\", `${{vbCanvas.minX}}`);
		                                                rect.setAttribute(\"y\", `${{vbCanvas.minY}}`);
		                                                rect.setAttribute(\"width\", `${{vbCanvas.width}}`);
		                                                rect.setAttribute(\"height\", `${{vbCanvas.height}}`);
		                                                rect.setAttribute(\"fill\", \"#FFFFFF\");
		                                                rect.setAttribute(\"fill-opacity\", \"0.001\");
		                                                rect.setAttribute(\"stroke\", \"none\");
		                                                rect.setAttribute(\"stroke-opacity\", \"0\");
		                                                rect.setAttribute(\"pointer-events\", \"none\");
		                                                if (!existing) {{
		                                                    const first = svgEl.firstChild;
		                                                    svgEl.insertBefore(rect, first);
		                                                }}
		                                            }}
		                                        }} catch (_e) {{}}

		                                        return new XMLSerializer().serializeToString(svgEl);
		                                    }}

                                    function getMaxWidthEmu(xmlDoc) {{
                                        try {{
                                            const sects = xmlDoc.getElementsByTagName("w:sectPr");
                                            const sect = sects && sects.length ? sects[sects.length - 1] : null;
                                            if (!sect) return 5486400;
                                            const pgSz = sect.getElementsByTagName("w:pgSz")[0];
                                            const pgMar = sect.getElementsByTagName("w:pgMar")[0];
                                            if (!pgSz || !pgMar) return 5486400;
                                            const pageW = parseInt(pgSz.getAttribute("w:w") || "", 10);
                                            const left = parseInt(pgMar.getAttribute("w:left") || "", 10);
                                            const right = parseInt(pgMar.getAttribute("w:right") || "", 10);
                                            if (!isFinite(pageW) || !isFinite(left) || !isFinite(right)) return 5486400;
                                            const twips = Math.max(1, pageW - left - right);
                                            return Math.round(twips * 635);
                                        }} catch (_e) {{
                                            return 5486400;
                                        }}
                                    }}

                                    function getChildByTag(parent, tag) {{
                                        const nodes = parent.getElementsByTagName(tag);
                                        return nodes && nodes.length ? nodes[0] : null;
                                    }}

                                    try {{
                                        await loadScript(jszipUrl, "JSZip");
                                        await loadScript(mermaidUrl, "mermaid");

	                                        try {{
		                                            window.mermaid.initialize({{
		                                                startOnLoad: false,
		                                                theme: "default",
			                                                themeVariables: {{
			                                                    background: themeBackground,
			                                                    fontFamily: "Calibri, Segoe UI, Arial, sans-serif",
			                                                    fontSize: "10pt",
			                                                }},
			                                                themeCSS: ".slice {{ font-size: 10pt !important; }}\\n.legend text {{ font-size: 10pt !important; }}\\n.pieTitleText {{ font-size: 10pt !important; }}",
			                                                fontFamily: "Calibri, Segoe UI, Arial, sans-serif",
			                                                securityLevel: "strict",
			                                                flowchart: {{ htmlLabels: false }},
			                                            }});
	                                        }} catch (_e) {{
                                        }}

                                        const bytes = decodeBase64ToUint8Array(base64Data);
                                        const zip = new window.JSZip();
                                        await zip.loadAsync(bytes);

                                        const docXml = await zip.file("word/document.xml").async("string");
                                        const relsXml = await zip.file("word/_rels/document.xml.rels").async("string");
                                        const parser = new DOMParser();
                                        const xmlDoc = parser.parseFromString(docXml, "application/xml");
                                        const relsDoc = parser.parseFromString(relsXml, "application/xml");

                                        const rels = relsDoc.getElementsByTagName("Relationship");
                                        const rIdToTarget = {{}};
                                        for (let i = 0; i < rels.length; i++) {{
                                            const rel = rels[i];
                                            const id = rel.getAttribute("Id");
                                            const target = rel.getAttribute("Target");
                                            if (id && target) rIdToTarget[id] = target;
                                        }}

                                        const maxWidthEmu = getMaxWidthEmu(xmlDoc);
                                        const maxWidthEmuScaled = Math.max(1, Math.round(maxWidthEmu * Math.min(1.0, Math.max(0.1, displayScale || 1.0))));

                                        const drawings = xmlDoc.getElementsByTagName("w:drawing");
                                        const placeholders = [];

                                        for (let i = 0; i < drawings.length; i++) {{
                                            const drawing = drawings[i];
                                            const docPr = getChildByTag(drawing, "wp:docPr");
                                            if (!docPr) continue;
                                            const descr = docPr.getAttribute("descr") || "";
                                            if (!descr.startsWith("MERMAID_SRC:")) continue;
                                            const encoded = descr.substring("MERMAID_SRC:".length);
                                            const code = decodeURIComponent(encoded);

                                            const blip = getChildByTag(drawing, "a:blip");
                                            const ridPng = blip ? blip.getAttribute("r:embed") : null;
                                            const svgBlip = getChildByTag(drawing, "asvg:svgBlip");
                                            const ridSvg = svgBlip ? svgBlip.getAttribute("r:embed") : null;

                                            const container = getChildByTag(drawing, "wp:inline") || getChildByTag(drawing, "wp:anchor");
                                            const extent = container ? getChildByTag(container, "wp:extent") : null;

                                            const xfrm = getChildByTag(drawing, "a:xfrm");
                                            const xfrmExt = xfrm ? getChildByTag(xfrm, "a:ext") : null;

                                            placeholders.push({{ code, ridPng, ridSvg, extent, xfrmExt, svgBlip }});
                                        }}

                                        if (!placeholders.length) {{
                                            const blob = new Blob([bytes], {{ type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }});
                                            downloadBlob(blob, filename);
                                            return;
                                        }}

                                        const renderResults = [];
                                        for (let i = 0; i < placeholders.length; i++) {{
                                            const item = placeholders[i];
                                            try {{
                                                const id = "owui-mermaid-" + i;
                                                const rendered = await window.mermaid.render(id, item.code);
                                                let svgText = rendered && rendered.svg ? rendered.svg : rendered;
                                                if (!svgText || typeof svgText !== "string") throw new Error("Mermaid vrátil prázdné SVG");

                                                svgText = normalizeSvgForWord(svgText);
                                                const hasForeignObject = /<foreignObject\\b/i.test(svgText);
                                                if (hasForeignObject && item.svgBlip) {{
                                                    try {{ item.svgBlip.parentNode && item.svgBlip.parentNode.removeChild(item.svgBlip); }} catch (_e) {{}}
                                                    item.ridSvg = null;
                                                }}

                                                const svgDoc = new DOMParser().parseFromString(svgText, "image/svg+xml");
                                                const svgEl = svgDoc.documentElement;
                                                const vb = parseViewBox(svgEl && svgEl.getAttribute ? svgEl.getAttribute("viewBox") : null);
                                                const ratio = vb && vb.width > 0 && vb.height > 0 ? (vb.width / vb.height) : (4/3);

                                                const widthEmu = maxWidthEmuScaled;
                                                const heightEmu = Math.max(1, Math.round(widthEmu / ratio));

                                                renderResults.push({{ item, svgText, widthEmu, heightEmu, success: true }});
                                            }} catch (err) {{
                                                console.error("Renderování Mermaid selhalo pro blok", i, err);
                                                renderResults.push({{ item, svgText: null, widthEmu: 0, heightEmu: 0, success: false }});
                                            }}
                                        }}

                                        async function svgToPng(svgText, targetWidthPx, targetHeightPx) {{
                                            const canvas = document.createElement("canvas");
                                            const ctx = canvas.getContext("2d");
                                            const scale = Math.max(1.0, pngScale || 1.0);
                                            canvas.width = Math.round(targetWidthPx * scale);
                                            canvas.height = Math.round(targetHeightPx * scale);
                                            ctx.setTransform(1, 0, 0, 1, 0, 0);
                                            if (bgFill) {{
                                                ctx.fillStyle = bgFill;
                                                ctx.fillRect(0, 0, canvas.width, canvas.height);
                                            }}
                                            ctx.scale(scale, scale);

                                            const img = new Image();
                                            await new Promise((resolve, reject) => {{
                                                img.onload = resolve;
                                                img.onerror = reject;
                                                img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgText)));
                                            }});

                                            ctx.drawImage(img, 0, 0, targetWidthPx, targetHeightPx);
                                            const pngDataUrl = canvas.toDataURL("image/png");
                                            return pngDataUrl.split(",")[1];
                                        }}

                                        const pngPromises = renderResults.map(async (result, i) => {{
                                            if (!result.success || !result.svgText) return null;
                                            const {{ item, widthEmu, heightEmu }} = result;
                                            if (!item.ridPng || !rIdToTarget[item.ridPng]) return null;
                                            
                                            const targetWidthPx = Math.max(1, Math.round(widthEmu / 9525));
                                            const targetHeightPx = Math.max(1, Math.round(heightEmu / 9525));
                                            
                                            try {{
                                                const pngBase64 = await svgToPng(result.svgText, targetWidthPx, targetHeightPx);
                                                return {{ index: i, pngBase64, path: "word/" + rIdToTarget[item.ridPng] }};
                                            }} catch (err) {{
                                                console.error("Konverze PNG selhala pro blok", i, err);
                                                return null;
                                            }}
                                        }});

                                        const pngResults = await Promise.all(pngPromises);

                                        for (let i = 0; i < renderResults.length; i++) {{
                                            const result = renderResults[i];
                                            if (!result.success) continue;
                                            
                                            const {{ item, svgText, widthEmu, heightEmu }} = result;
                                            
                                            if (item.extent) {{
                                                item.extent.setAttribute("cx", `${{widthEmu}}`);
                                                item.extent.setAttribute("cy", `${{heightEmu}}`);
                                            }}
                                            if (item.xfrmExt) {{
                                                item.xfrmExt.setAttribute("cx", `${{widthEmu}}`);
                                                item.xfrmExt.setAttribute("cy", `${{heightEmu}}`);
                                            }}

                                            if (item.ridSvg && rIdToTarget[item.ridSvg]) {{
                                                zip.file("word/" + rIdToTarget[item.ridSvg], svgText);
                                            }}
                                        }}

                                        for (const pngResult of pngResults) {{
                                            if (pngResult && pngResult.pngBase64) {{
                                                zip.file(pngResult.path, pngResult.pngBase64, {{ base64: true }});
                                            }}
                                        }}

                                        const newDocXml = new XMLSerializer().serializeToString(xmlDoc);
                                        zip.file("word/document.xml", newDocXml);

                                        const finalBlob = await zip.generateAsync({{
                                            type: "blob",
                                            compression: "DEFLATE",
                                            compressionOptions: {{ level: 6 }},
                                        }});
                                        downloadBlob(finalBlob, filename);
                                    }} catch (error) {{
                                        console.error("Export pipeline selhal:", error);
                                        const bytes = decodeBase64ToUint8Array(base64Data);
                                        const blob = new Blob([bytes], {{ type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }});
                                        downloadBlob(blob, filename);
                                    }}
                                }})();
                                """
                            },
                        }
                    )

                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": self._get_msg("exported"),
                            "done": True,
                        },
                    }
                )

                await self._emit_notification(
                    __event_emitter__,
                    self._get_msg("success", filename=filename),
                    "success",
                )

                return {"message": "Stahování spuštěno"}

            except Exception as e:
                logger.exception(f"Chyba při exportu do Wordu: {str(e)}")
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": self._get_msg("export_failed", error=str(e)),
                            "done": True,
                        },
                    }
                )
                await self._emit_notification(
                    __event_emitter__,
                    self._get_msg("error_export", error=str(e)),
                    "error",
                )

    async def generate_title_using_ai(
        self, body: dict, content: str, user_id: str, request: Any
    ) -> str:
        if not request:
            return ""

        try:
            user_obj = Users.get_user_by_id(user_id)
            model = body.get("model")

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Jsi užitečný asistent. Vygeneruj krátký, stručný název (max 10 slov) pro následující text. Nepoužívej uvozovky. Vypiš pouze název.",
                    },
                    {"role": "user", "content": content[:2000]},  # Omezení délky obsahu
                ],
                "stream": False,
            }

            response = await generate_chat_completion(request, payload, user_obj)
            if response and "choices" in response:
                return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Chyba při generování názvu: {e}")

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

    def extract_chat_title(self, body: dict) -> str:
        """Extrahuje název chatu z běžných polí payloadu."""
        if not isinstance(body, dict):
            return ""

        candidates = []

        for key in ("chat", "conversation"):
            if isinstance(body.get(key), dict):
                candidates.append(body.get(key, {}).get("title", ""))

        for key in ("title", "chat_title"):
            value = body.get(key)
            if isinstance(value, str):
                candidates.append(value)

        for candidate in candidates:
            if candidate and isinstance(candidate, str):
                return candidate.strip()
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
                chat = Chats.get_chat_by_id_and_user_id(id=chat_id, user_id=user_id)
                if chat:
                    return chat
            return Chats.get_chat_by_id(chat_id)

        try:
            chat = await asyncio.to_thread(_load_chat)
        except Exception as exc:
            logger.warning(f"Nepodařilo se načíst chat {chat_id}: {exc}")
            return ""

        if not chat:
            return ""

        data = getattr(chat, "chat", {}) or {}
        title = data.get("title") or getattr(chat, "title", "")
        return title.strip() if isinstance(title, str) else ""

    def clean_filename(self, name: str) -> str:
        """Vyčistí nepovolené znaky z názvu souboru a odstraní emoji."""
        if not isinstance(name, str):
            return ""

        def _is_emoji_codepoint(codepoint: int) -> bool:
            # Běžné rozsahy emoji + regionální indikátory vlajek.
            return (
                0x1F000 <= codepoint <= 0x1FAFF
                or 0x1F1E6 <= codepoint <= 0x1F1FF
                or 0x2600 <= codepoint <= 0x26FF
                or 0x2700 <= codepoint <= 0x27BF
                or 0x2300 <= codepoint <= 0x23FF
                or 0x2B00 <= codepoint <= 0x2BFF
            )

        def _is_emoji_modifier(codepoint: int) -> bool:
            # VS15/VS16, ZWJ, keycap, odstíny pleti a znaky tagů používané v některých emoji sekvencích.
            return (
                codepoint in (0x200D, 0xFE0E, 0xFE0F, 0x20E3)
                or 0x1F3FB <= codepoint <= 0x1F3FF
                or 0xE0020 <= codepoint <= 0xE007F
            )

        without_emoji = "".join(
            ch
            for ch in name
            if not (_is_emoji_codepoint(ord(ch)) or _is_emoji_modifier(ord(ch)))
        )
        cleaned = re.sub(r'[\\/*?:"<>|]', "", without_emoji)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
        return cleaned[:50].strip()

    # ============ ČÁST 1: IMAGE HANDLING METODY ============
    # TODO: Vlož sem následující metody z originálního kódu:
    # - _max_embed_image_bytes
    # - _extract_owui_api_file_id
    # - _read_file_bytes_limited
    # - _decode_base64_limited
    # - _image_bytes_from_data_url
    # - _read_from_s3
    # - _image_bytes_from_owui_file_id
    # - _add_image_placeholder
    # - _try_embed_image
    # - _embed_markdown_image
    #
    # ZDROJ: Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
    # Nebo: https://github.com/Fu-Jie/awesome-openwebui
    # ======================================================
    
    # ============ ČÁST 2: MARKDOWN PARSING METODY ============
    # TODO: Vlož sem následující metody z originálního kódu:
    # - markdown_to_docx
    # - _extract_single_line_math
    # - _strip_reasoning_blocks
    #
    # ZDROJ: Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
    # ======================================================
    
    # ============ ČÁST 3: MATH A CITACE METODY ============
    # TODO: Vlož sem následující metody z originálního kódu:
    # - _add_display_equation
    # - _wrap_omml_for_word
    # - _build_citation_refs
    # - _add_bookmark
    # - _add_internal_hyperlink
    # - _add_references_section
    #
    # ZDROJ: Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
    # ======================================================
    
    # ============ ČÁST 4: MERMAID METODY ============
    # TODO: Vlož sem následující metody z originálního kódu:
    # - _parse_fence_info
    # - _normalize_mermaid_text
    # - _prepare_mermaid_for_js
    # - _png_with_text_chunk
    # - _make_mermaid_placeholder_png
    # - _dummy_mermaid_svg_bytes
    # - _insert_mermaid_placeholder
    # - _extract_mermaid_title
    # - _strip_mermaid_title_for_render
    # - _ensure_caption_style
    # - _add_mermaid_caption
    #
    # ZDROJ: Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
    # ======================================================
    
    # ============ ČÁST 5: DOCUMENT STYLING METODY ============
    # TODO: Vlož sem následující metody z originálního kódu:
    # - _available_block_width
    # - _attach_svg_blip
    # - set_document_default_font
    #
    # ZDROJ: Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
    # ======================================================
    
    # ============ ČÁST 6: TEXT FORMATTING METODY ============
    # TODO: Vlož sem následující metody z originálního kódu:
    # - add_heading
    # - add_paragraph
    # - add_formatted_text
    # - _add_text_run
    # - _add_inline_code
    # - _add_hyperlink_code
    # - _add_inline_segments
    # - _normalize_url
    # - _add_hyperlink
    # - _add_inline_equation
    # - _omml_oMath_element
    #
    # ZDROJ: Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
    # ======================================================
    
    # ============ ČÁST 7: BLOCK ELEMENTS METODY ============
    # TODO: Vlož sem následující metody z originálního kódu:
    # - add_code_block
    # - add_table
    # - _set_table_cell_margins
    # - _set_table_header_row_repeat
    # - add_list_to_doc
    # - add_horizontal_rule
    # - add_blockquote
    #
    # ZDROJ: Open WebUI → Admin Panel → Functions → Export to Word (Enhanced) → Edit
    # Nebo: https://github.com/Fu-Jie/awesome-openwebui
    # ======================================================
