"""
title: Hluboký ponor
author: Fu-Jie
author_url: https://github.com/Fu-Jie
funding_url: https://github.com/Fu-Jie/awesome-openwebui
version: 1.0.0
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xMiA3djE0Ii8+PHBhdGggZD0iTTMgMThhMSAxIDAgMCAxLTEtMVY0YTEgMSAwIDAgMSAxLTFoNWE0IDQgMCAwIDEgNCA0IDQgNCAwIDAgMSA0LTRoNWExIDEgMCAwIDEgMSAxdjEzYTEgMSAwIDAgMS0xIDFoLTZhMyAzIDAgMCAwLTMgMyAzIDMgMCAwIDAtMy0zeiIvPjxwYXRoIGQ9Ik02IDEyaDIiLz48cGF0aCBkPSJNMTYgMTJoMiIvPjwvc3ZnPg==
requirements: markdown
description: Komplexní myšlenková čočka, která se hluboce ponoří do jakéhokoli obsahu - od kontextu přes logiku, poznatky až po akční cesty.
"""

# Standardní knihovny
import re
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime

# Externí knihovny
from pydantic import BaseModel, Field
from fastapi import Request
import markdown

# OpenWebUI importy
from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import Users

# Nastavení logování
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =================================================================
# HTML Šablona - Procesně orientovaný design s podporou motivů
# =================================================================
HTML_WRAPPER_TEMPLATE = """
<!-- OPENWEBUI_PLUGIN_OUTPUT -->
<!DOCTYPE html>
<html lang="{user_language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --dd-bg-primary: #ffffff;
            --dd-bg-secondary: #f8fafc;
            --dd-bg-tertiary: #f1f5f9;
            --dd-text-primary: #0f172a;
            --dd-text-secondary: #334155;
            --dd-text-dim: #64748b;
            --dd-border: #e2e8f0;
            --dd-accent: #3b82f6;
            --dd-accent-soft: #eff6ff;
            --dd-header-gradient: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            --dd-shadow: 0 10px 40px rgba(0,0,0,0.06);
            --dd-code-bg: #f1f5f9;
        }
        .theme-dark {
            --dd-bg-primary: #1e293b;
            --dd-bg-secondary: #0f172a;
            --dd-bg-tertiary: #334155;
            --dd-text-primary: #f1f5f9;
            --dd-text-secondary: #e2e8f0;
            --dd-text-dim: #94a3b8;
            --dd-border: #475569;
            --dd-accent: #60a5fa;
            --dd-accent-soft: rgba(59, 130, 246, 0.15);
            --dd-header-gradient: linear-gradient(135deg, #0f172a 0%, #1e1e2e 100%);
            --dd-shadow: 0 10px 40px rgba(0,0,0,0.3);
            --dd-code-bg: #334155;
        }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            margin: 0; 
            padding: 10px; 
            background-color: transparent; 
        }
        #main-container { 
            display: flex; 
            flex-direction: column;
            gap: 24px; 
            width: 100%;
            max-width: 900px;
            margin: 0 auto;
        }
        .plugin-item { 
            background: var(--dd-bg-primary); 
            border-radius: 24px; 
            box-shadow: var(--dd-shadow); 
            overflow: hidden; 
            border: 1px solid var(--dd-border); 
        }
        /* STYLES_INSERTION_POINT */
    </style>
</head>
<body>
    <div id="main-container">
        <!-- CONTENT_INSERTION_POINT -->
    </div>
    <!-- SCRIPTS_INSERTION_POINT -->
    <script>
    (function() {
        const parseColorLuma = (colorStr) => {
            if (!colorStr) return null;
            let m = colorStr.match(/^#?([0-9a-f]{6})$/i);
            if (m) {
                const hex = m[1];
                const r = parseInt(hex.slice(0, 2), 16);
                const g = parseInt(hex.slice(2, 4), 16);
                const b = parseInt(hex.slice(4, 6), 16);
                return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
            }
            m = colorStr.match(/rgba?\\s*\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)/i);
            if (m) {
                const r = parseInt(m[1], 10);
                const g = parseInt(m[2], 10);
                const b = parseInt(m[3], 10);
                return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
            }
            return null;
        };
        const getThemeFromMeta = (doc) => {
            const metas = Array.from((doc || document).querySelectorAll('meta[name="theme-color"]'));
            if (!metas.length) return null;
            const color = metas[metas.length - 1].content.trim();
            const luma = parseColorLuma(color);
            if (luma === null) return null;
            return luma < 0.5 ? 'dark' : 'light';
        };
        const getParentDocumentSafe = () => {
            try {
                if (!window.parent || window.parent === window) return null;
                const pDoc = window.parent.document;
                void pDoc.title;
                return pDoc;
            } catch (err) { return null; }
        };
        const getThemeFromParentClass = () => {
            try {
                if (!window.parent || window.parent === window) return null;
                const pDoc = window.parent.document;
                const html = pDoc.documentElement;
                const body = pDoc.body;
                const htmlClass = html ? html.className : '';
                const bodyClass = body ? body.className : '';
                const htmlDataTheme = html ? html.getAttribute('data-theme') : '';
                if (htmlDataTheme === 'dark' || bodyClass.includes('dark') || htmlClass.includes('dark')) return 'dark';
                if (htmlDataTheme === 'light' || bodyClass.includes('light') || htmlClass.includes('light')) return 'light';
                return null;
            } catch (err) { return null; }
        };
        const setTheme = () => {
            const parentDoc = getParentDocumentSafe();
            const metaTheme = parentDoc ? getThemeFromMeta(parentDoc) : null;
            const parentClassTheme = getThemeFromParentClass();
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            const chosen = metaTheme || parentClassTheme || (prefersDark ? 'dark' : 'light');
            document.documentElement.classList.toggle('theme-dark', chosen === 'dark');
        };
        setTheme();
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', setTheme);
        }
    })();
    </script>
</body>
</html>
"""

# =================================================================
# LLM Prompty - Řetězec hlubokého myšlení
# =================================================================

SYSTEM_PROMPT = """
Jsi analytik Hlubokého ponoru. Tvým cílem je provést uživatele komplexním myšlenkovým procesem, od povrchového pochopení až po hlubokou strategickou akci.

## Struktura myšlení (PŘÍSNÁ)

MUSÍŠ analyzovat vstup napříč těmito čtyřmi specifickými dimenzemi:

### 1. 🔍 Kontext (Co?)
Poskytni panoramatický přehled na vysoké úrovni. O čem je tento obsah? Jaká je jádro situace, pozadí nebo problém, který je řešen? (2-3 odstavce)

### 2. 🧠 Logika (Proč?)
Rozlož základní strukturu. Jak je argument postaven? Jaká je úvaha, skryté předpoklady nebo mentální modely v akci? (Odrážky)

### 3. 💎 Poznatek (A co z toho?)
Extrahuj ne zjevnou hodnotu. Jaké jsou "Aha!" momenty? Jaké jsou důsledky, slepé skvrny nebo jedinečné perspektivy odhalené? (Odrážky)

### 4. 🚀 Cesta (A teď co?)
Definuj strategický směr. Jaké jsou konkrétní, prioritizované další kroky? Jak lze tuto znalost okamžitě aplikovat? (Akční kroky)

## Pravidla
- Výstup v jazyce uživatele.
- Udržuj profesionální, analytický, ale inspirativní tón.
- Zaměř se na *proces* pochopení, ne jen na výsledek.
- Žádné pozdravy ani meta-komentáře.
"""

USER_PROMPT = """
Spusť Hluboký ponor do následujícího obsahu:

**Kontext uživatele:**
- Uživatel: {user_name}
- Čas: {current_date_time_str}
- Jazyk: {user_language}

**Obsah k analýze:**
```
{long_text_content}
```

Prosím proveď celý myšlenkový řetězec: Kontext → Logika → Poznatek → Cesta.
"""

# =================================================================
# Premium CSS Design - Motiv Hlubokého ponoru
# =================================================================

CSS_TEMPLATE = """
        .deep-dive {
            font-family: 'Inter', -apple-system, system-ui, sans-serif;
            color: var(--dd-text-secondary);
        }

        .dd-header {
            background: var(--dd-header-gradient);
            padding: 40px 32px;
            color: white;
            position: relative;
        }

        .dd-header-badge {
            display: inline-block;
            padding: 4px 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 16px;
        }

        .dd-title {
            font-size: 2rem;
            font-weight: 800;
            margin: 0 0 12px 0;
            letter-spacing: -0.02em;
        }

        .dd-meta {
            display: flex;
            gap: 20px;
            font-size: 0.85rem;
            opacity: 0.7;
        }

        .dd-body {
            padding: 32px;
            display: flex;
            flex-direction: column;
            gap: 40px;
            position: relative;
            background: var(--dd-bg-primary);
        }

        /* Myšlenková čára */
        .dd-body::before {
            content: '';
            position: absolute;
            left: 52px;
            top: 40px;
            bottom: 40px;
            width: 2px;
            background: var(--dd-border);
            z-index: 0;
        }

        .dd-step {
            position: relative;
            z-index: 1;
            display: flex;
            gap: 24px;
        }

        .dd-step-icon {
            flex-shrink: 0;
            width: 40px;
            height: 40px;
            background: var(--dd-bg-primary);
            border: 2px solid var(--dd-border);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            transition: all 0.3s ease;
        }

        .dd-step:hover .dd-step-icon {
            border-color: var(--dd-accent);
            transform: scale(1.1);
        }

        .dd-step-content {
            flex: 1;
        }

        .dd-step-label {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--dd-accent);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 4px;
        }

        .dd-step-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--dd-text-primary);
            margin: 0 0 16px 0;
        }

        .dd-text {
            line-height: 1.7;
            font-size: 1rem;
        }

        .dd-text p { margin-bottom: 16px; }
        .dd-text p:last-child { margin-bottom: 0; }

        .dd-list {
            list-style: none;
            padding: 0;
            margin: 0;
            display: grid;
            gap: 12px;
        }

        .dd-list-item {
            background: var(--dd-bg-secondary);
            padding: 16px 20px;
            border-radius: 12px;
            border-left: 4px solid var(--dd-border);
            transition: all 0.2s ease;
        }

        .dd-list-item:hover {
            background: var(--dd-bg-tertiary);
            border-left-color: var(--dd-accent);
            transform: translateX(4px);
        }

        .dd-list-item strong {
            color: var(--dd-text-primary);
            display: block;
            margin-bottom: 4px;
        }

        .dd-path-item {
            background: var(--dd-accent-soft);
            border-left-color: var(--dd-accent);
        }

        .dd-footer {
            padding: 24px 32px;
            background: var(--dd-bg-secondary);
            border-top: 1px solid var(--dd-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--dd-text-dim);
        }

        .dd-tag {
            padding: 2px 8px;
            background: var(--dd-bg-tertiary);
            border-radius: 4px;
            font-weight: 600;
        }

        .dd-text code,
        .dd-list-item code {
            background: var(--dd-code-bg);
            color: var(--dd-text-primary);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
            font-size: 0.85em;
        }

        .dd-list-item em {
            font-style: italic;
            color: var(--dd-text-dim);
        }
"""

CONTENT_TEMPLATE = """
        <div class="deep-dive">
            <div class="dd-header">
                <div class="dd-header-badge">Myšlenkový proces</div>
                <h1 class="dd-title">Analýza hlubokého ponoru</h1>
                <div class="dd-meta">
                    <span>👤 {user_name}</span>
                    <span>📅 {current_date_time_str}</span>
                    <span>📊 {word_count} slov</span>
                </div>
            </div>
            <div class="dd-body">
                <!-- Krok 1: Kontext -->
                <div class="dd-step">
                    <div class="dd-step-icon">🔍</div>
                    <div class="dd-step-content">
                        <div class="dd-step-label">Fáze 01</div>
                        <h2 class="dd-step-title">Kontext</h2>
                        <div class="dd-text">{context_html}</div>
                    </div>
                </div>

                <!-- Krok 2: Logika -->
                <div class="dd-step">
                    <div class="dd-step-icon">🧠</div>
                    <div class="dd-step-content">
                        <div class="dd-step-label">Fáze 02</div>
                        <h2 class="dd-step-title">Logika</h2>
                        <div class="dd-text">{logic_html}</div>
                    </div>
                </div>

                <!-- Krok 3: Poznatek -->
                <div class="dd-step">
                    <div class="dd-step-icon">💎</div>
                    <div class="dd-step-content">
                        <div class="dd-step-label">Fáze 03</div>
                        <h2 class="dd-step-title">Poznatek</h2>
                        <div class="dd-text">{insight_html}</div>
                    </div>
                </div>

                <!-- Krok 4: Cesta -->
                <div class="dd-step">
                    <div class="dd-step-icon">🚀</div>
                    <div class="dd-step-content">
                        <div class="dd-step-label">Fáze 04</div>
                        <h2 class="dd-step-title">Cesta</h2>
                        <div class="dd-text">{path_html}</div>
                    </div>
                </div>
            </div>
            <div class="dd-footer">
                <span>Deep Dive Engine v1.0</span>
                <span><span class="dd-tag">AI-Powered</span></span>
            </div>
        </div>
"""


class Action:
    class Valves(BaseModel):
        SHOW_STATUS: bool = Field(
            default=True,
            description="Zda zobrazovat aktualizace stavu operace.",
        )
        MODEL_ID: str = Field(
            default="",
            description="ID LLM modelu pro analýzu. Prázdné = použít aktuální model.",
        )
        MIN_TEXT_LENGTH: int = Field(
            default=200,
            description="Minimální délka textu pro hluboký ponor (znaky).",
        )
        CLEAR_PREVIOUS_HTML: bool = Field(
            default=True,
            description="Zda vymazat předchozí výsledky pluginu.",
        )
        MESSAGE_COUNT: int = Field(
            default=1,
            description="Počet nedávných zpráv k analýze.",
        )

    def __init__(self):
        self.valves = self.Valves()

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

    def _process_llm_output(self, llm_output: str) -> Dict[str, str]:
        """Parsuje výstup LLM a převádí na stylovaný HTML."""
        # Extrahovat sekce pomocí flexibilního regexu
        context_match = re.search(
            r"###\s*1\.\s*🔍?\s*Kontext\s*\((.*?)\)\s*\n(.*?)(?=\n###|$)",
            llm_output,
            re.DOTALL | re.IGNORECASE,
        )
        logic_match = re.search(
            r"###\s*2\.\s*🧠?\s*Logika\s*\((.*?)\)\s*\n(.*?)(?=\n###|$)",
            llm_output,
            re.DOTALL | re.IGNORECASE,
        )
        insight_match = re.search(
            r"###\s*3\.\s*💎?\s*Poznatek\s*\((.*?)\)\s*\n(.*?)(?=\n###|$)",
            llm_output,
            re.DOTALL | re.IGNORECASE,
        )
        path_match = re.search(
            r"###\s*4\.\s*🚀?\s*Cesta\s*\((.*?)\)\s*\n(.*?)(?=\n###|$)",
            llm_output,
            re.DOTALL | re.IGNORECASE,
        )

        # Záložní možnost pokud je číslování jiné
        if not context_match:
            context_match = re.search(
                r"###\s*🔍?\s*Kontext.*?\n(.*?)(?=\n###|$)",
                llm_output,
                re.DOTALL | re.IGNORECASE,
            )
        if not logic_match:
            logic_match = re.search(
                r"###\s*🧠?\s*Logika.*?\n(.*?)(?=\n###|$)",
                llm_output,
                re.DOTALL | re.IGNORECASE,
            )
        if not insight_match:
            insight_match = re.search(
                r"###\s*💎?\s*Poznatek.*?\n(.*?)(?=\n###|$)",
                llm_output,
                re.DOTALL | re.IGNORECASE,
            )
        if not path_match:
            path_match = re.search(
                r"###\s*🚀?\s*Cesta.*?\n(.*?)(?=\n###|$)",
                llm_output,
                re.DOTALL | re.IGNORECASE,
            )

        context_md = (
            context_match.group(1 if context_match.lastindex == 1 else 2).strip()
            if context_match
            else ""
        )
        logic_md = (
            logic_match.group(1 if logic_match.lastindex == 1 else 2).strip()
            if logic_match
            else ""
        )
        insight_md = (
            insight_match.group(1 if insight_match.lastindex == 1 else 2).strip()
            if insight_match
            else ""
        )
        path_md = (
            path_match.group(1 if path_match.lastindex == 1 else 2).strip()
            if path_match
            else ""
        )

        if not any([context_md, logic_md, insight_md, path_md]):
            context_md = llm_output.strip()
            logger.warning("Výstup LLM nesledoval formát. Používá se jako kontext.")

        md_extensions = ["nl2br"]

        context_html = (
            markdown.markdown(context_md, extensions=md_extensions)
            if context_md
            else '<p class="dd-no-content">Kontext nebyl extrahován.</p>'
        )
        logic_html = (
            self._process_list_items(logic_md, "logic")
            if logic_md
            else '<p class="dd-no-content">Logika nebyla dekonstruována.</p>'
        )
        insight_html = (
            self._process_list_items(insight_md, "insight")
            if insight_md
            else '<p class="dd-no-content">Poznatky nebyly nalezeny.</p>'
        )
        path_html = (
            self._process_list_items(path_md, "path")
            if path_md
            else '<p class="dd-no-content">Cesta nebyla definována.</p>'
        )

        return {
            "context_html": context_html,
            "logic_html": logic_html,
            "insight_html": insight_html,
            "path_html": path_html,
        }

    def _process_list_items(self, md_content: str, section_type: str) -> str:
        """Převádí markdown seznam na stylované HTML karty s plnou podporou markdownu."""
        lines = md_content.strip().split("\n")
        items = []
        current_paragraph = []

        for line in lines:
            line = line.strip()

            # Kontrola položky seznamu (odrážka nebo číslovaná)
            bullet_match = re.match(r"^[-*]\s+(.+)$", line)
            numbered_match = re.match(r"^\d+\.\s+(.+)$", line)

            if bullet_match or numbered_match:
                # Vyprázdnit jakýkoli nahromaděný odstavec
                if current_paragraph:
                    para_text = " ".join(current_paragraph)
                    para_html = self._convert_inline_markdown(para_text)
                    items.append(f"<p>{para_html}</p>")
                    current_paragraph = []

                # Extrahovat obsah položky seznamu
                text = (
                    bullet_match.group(1) if bullet_match else numbered_match.group(1)
                )

                # Zpracovat vzor tučného nadpisu: **Nadpis:** Popis nebo **Nadpis**: Popis
                title_match = re.match(r"\*\*(.+?)\*\*[:\s]*(.*)$", text)
                if title_match:
                    title = self._convert_inline_markdown(title_match.group(1))
                    desc = self._convert_inline_markdown(title_match.group(2).strip())
                    path_class = "dd-path-item" if section_type == "path" else ""
                    item_html = f'<div class="dd-list-item {path_class}"><strong>{title}</strong>{desc}</div>'
                else:
                    text_html = self._convert_inline_markdown(text)
                    path_class = "dd-path-item" if section_type == "path" else ""
                    item_html = (
                        f'<div class="dd-list-item {path_class}">{text_html}</div>'
                    )
                items.append(item_html)
            elif line and not line.startswith("#"):
                # Nahromadit text odstavce
                current_paragraph.append(line)
            elif not line and current_paragraph:
                # Prázdný řádek ukončuje odstavec
                para_text = " ".join(current_paragraph)
                para_html = self._convert_inline_markdown(para_text)
                items.append(f"<p>{para_html}</p>")
                current_paragraph = []

        # Vyprázdnit zbývající odstavec
        if current_paragraph:
            para_text = " ".join(current_paragraph)
            para_html = self._convert_inline_markdown(para_text)
            items.append(f"<p>{para_html}</p>")

        if items:
            return f'<div class="dd-list">{" ".join(items)}</div>'
        return f'<p class="dd-no-content">Položky nebyly nalezeny.</p>'

    def _convert_inline_markdown(self, text: str) -> str:
        """Převádí inline markdown (tučné, kurzíva, kód) na HTML."""
        # Převést inline kód: `kód` -> <code>kód</code>
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Převést tučné: **text** -> <strong>text</strong>
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Převést kurzívu: *text* -> <em>text</em> (ale ne uvnitř **)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        return text

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
        """Vysílá událost oznámení."""
        if emitter:
            await emitter(
                {"type": "notification", "data": {"type": ntype, "content": content}}
            )

    def _remove_existing_html(self, content: str) -> str:
        """Odstraňuje existující HTML generované pluginem."""
        pattern = r"```html\s*<!-- OPENWEBUI_PLUGIN_OUTPUT -->[\s\S]*?```"
        return re.sub(pattern, "", content).strip()

    def _extract_text_content(self, content) -> str:
        """Extrahuje text z obsahu zprávy."""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(text_parts)
        return str(content) if content else ""

    def _merge_html(
        self,
        existing_html: str,
        new_content: str,
        new_styles: str = "",
        user_language: str = "cs-CZ",
    ) -> str:
        """Sloučí nový obsah do HTML kontejneru."""
        if "<!-- OPENWEBUI_PLUGIN_OUTPUT -->" in existing_html:
            base_html = re.sub(r"^```html\s*", "", existing_html)
            base_html = re.sub(r"\s*```$", "", base_html)
        else:
            base_html = HTML_WRAPPER_TEMPLATE.replace("{user_language}", user_language)

        wrapped = f'<div class="plugin-item">\n{new_content}\n</div>'

        if new_styles:
            base_html = base_html.replace(
                "/* STYLES_INSERTION_POINT */",
                f"{new_styles}\n/* STYLES_INSERTION_POINT */",
            )

        base_html = base_html.replace(
            "<!-- CONTENT_INSERTION_POINT -->",
            f"{wrapped}\n<!-- CONTENT_INSERTION_POINT -->",
        )

        return base_html.strip()

    def _build_content_html(self, context: dict) -> str:
        """Vytvoří obsah HTML."""
        html = CONTENT_TEMPLATE
        for key, value in context.items():
            html = html.replace(f"{{{key}}}", str(value))
        return html

    async def action(
        self,
        body: dict,
        __user__: Optional[Dict[str, Any]] = None,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None,
        __request__: Optional[Request] = None,
    ) -> Optional[dict]:
        logger.info("Akce: Hluboký ponor v1.0.0 spuštěna")

        user_ctx = self._get_user_context(__user__)
        user_id = user_ctx["user_id"]
        user_name = user_ctx["user_name"]
        user_language = user_ctx["user_language"]

        now = datetime.now()
        current_date_time_str = now.strftime("%d. %m. %Y %H:%M")

        original_content = ""
        try:
            messages = body.get("messages", [])
            if not messages:
                raise ValueError("Nebyly nalezeny žádné zprávy.")

            message_count = min(self.valves.MESSAGE_COUNT, len(messages))
            recent_messages = messages[-message_count:]

            aggregated_parts = []
            for msg in recent_messages:
                text = self._extract_text_content(msg.get("content"))
                if text:
                    aggregated_parts.append(text)

            if not aggregated_parts:
                raise ValueError("Nebyl nalezen žádný textový obsah.")

            original_content = "\n\n---\n\n".join(aggregated_parts)
            word_count = len(original_content.split())

            if len(original_content) < self.valves.MIN_TEXT_LENGTH:
                msg = f"Obsah příliš krátký ({len(original_content)} znaků). Hluboký ponor vyžaduje alespoň {self.valves.MIN_TEXT_LENGTH} znaků pro smysluplnou analýzu."
                await self._emit_notification(__event_emitter__, msg, "warning")
                return {"messages": [{"role": "assistant", "content": f"⚠️ {msg}"}]}

            await self._emit_notification(
                __event_emitter__, "🌊 Spouštím myšlenkový proces Hlubokého ponoru...", "info"
            )
            await self._emit_status(
                __event_emitter__, "🌊 Hluboký ponor: Analyzuji kontext a logiku...", False
            )

            prompt = USER_PROMPT.format(
                user_name=user_name,
                current_date_time_str=current_date_time_str,
                user_language=user_language,
                long_text_content=original_content,
            )

            model = self.valves.MODEL_ID or body.get("model")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            }

            user_obj = Users.get_user_by_id(user_id)
            if not user_obj:
                raise ValueError(f"Uživatel nenalezen: {user_id}")

            response = await generate_chat_completion(__request__, payload, user_obj)
            llm_output = response["choices"][0]["message"]["content"]

            processed = self._process_llm_output(llm_output)

            context = {
                "user_name": user_name,
                "current_date_time_str": current_date_time_str,
                "word_count": word_count,
                **processed,
            }

            content_html = self._build_content_html(context)

            # Zpracovat existující HTML
            existing = ""
            match = re.search(
                r"```html\s*(<!-- OPENWEBUI_PLUGIN_OUTPUT -->[\s\S]*?)```",
                original_content,
            )
            if match:
                existing = match.group(1)

            if self.valves.CLEAR_PREVIOUS_HTML or not existing:
                original_content = self._remove_existing_html(original_content)
                final_html = self._merge_html(
                    "", content_html, CSS_TEMPLATE, user_language
                )
            else:
                original_content = self._remove_existing_html(original_content)
                final_html = self._merge_html(
                    existing, content_html, CSS_TEMPLATE, user_language
                )

            body["messages"][-1][
                "content"
            ] = f"{original_content}\n\n```html\n{final_html}\n```"

            await self._emit_status(__event_emitter__, "🌊 Hluboký ponor dokončen!", True)
            await self._emit_notification(
                __event_emitter__,
                f"🌊 Hluboký ponor dokončen, {user_name}! Myšlenkový řetězec vygenerován.",
                "success",
            )

        except Exception as e:
            logger.error(f"Chyba Hlubokého ponoru: {e}", exc_info=True)
            body["messages"][-1][
                "content"
            ] = f"{original_content}\n\n❌ **Chyba:** {str(e)}"
            await self._emit_status(__event_emitter__, "Hluboký ponor selhal.", True)
            await self._emit_notification(
                __event_emitter__, f"Chyba: {str(e)}", "error"
            )

        return body
