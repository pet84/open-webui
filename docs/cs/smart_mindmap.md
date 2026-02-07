"""
title: 🧠 Chytrá myšlenková mapa
author: Fu-Jie
author_url: https://github.com/Fu-Jie/awesome-openwebui
funding_url: https://github.com/open-webui
funding_url: https://github.com/Fu-Jie/awesome-openwebui
version: 0.9.1
openwebui_id: 3094c59a-b4dd-4e0c-9449-15e2dd547dc4
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxyZWN0IHg9IjE2IiB5PSIxNiIgd2lkdGg9IjYiIGhlaWdodD0iNiIgcng9IjEiLz48cmVjdCB4PSIyIiB5PSIxNiIgd2lkdGg9IjYiIGhlaWdodD0iNiIgcng9IjEiLz48cmVjdCB4PSI5IiB5PSIyIiB3aWR0aD0iNiIgaGVpZ2h0PSI2IiByeD0iMSIvPjxwYXRoIGQ9Ik01IDE2di0zYTEgMSAwIDAgMSAxLTFoMTJhMSAxIDAgMCAxIDEgMXYzIi8+PHBhdGggZD0iTTEyIDEyVjgiLz48L3N2Zz4=
description: Inteligentně analyzuje textový obsah a generuje interaktivní myšlenkové mapy pro strukturování a vizualizaci znalostí.
"""

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, Dict, Optional
from zoneinfo import ZoneInfo

from fastapi import Request
from pydantic import BaseModel, Field

from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import Users

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT_MINDMAP_ASSISTANT = """
Jsi profesionální asistent pro generování myšlenkových map. Umíš efektivně analyzovat dlouhý text od uživatele a strukturovat jeho hlavní témata, klíčové koncepty, větve a podvětve do standardní Markdown syntaxe pro vykreslení pomocí Markmap.js.

Přísně dodržuj tyto pokyny:
-   **Jazyk**: Veškerý výstup musí být v jazyce specifikovaném uživatelem.
-   **Formát**: Tvůj výstup musí být striktně ve formátu Markdown seznamu, obalený pomocí ```markdown a ```.
    -   Použij `#` pro definici centrálního tématu (kořenový uzel).
    -   Použij `-` s dvoumezerovým odsazením pro reprezentaci větví a podvětví.
-   **Obsah**:
    -   Identifikuj centrální téma textu jako nadpis `#`.
    -   Identifikuj hlavní koncepty jako položky seznamu první úrovně.
    -   Identifikuj podpůrné detaily nebo podkoncepty jako vnořené položky seznamu.
    -   Obsah uzlů by měl být stručný a jasný, bez zbytečné upovídanosti.
-   **Výstup pouze Markdown syntaxe**: Nepřidávej žádné dodatečné pozdravy, vysvětlení nebo průvodní text.
-   **Pokud je text příliš krátký nebo nelze vygenerovat platnou myšlenkovou mapu**: Vypiš jednoduchý Markdown seznam indikující nemožnost generování, například:
    ```markdown
    # Nelze vygenerovat myšlenkovou mapu
    - Důvod: Nedostatečný nebo nejasný textový obsah
    ```
"""

import json

USER_PROMPT_GENERATE_MINDMAP = """
Prosím analyzuj následující dlouhý text a strukturuj jeho hlavní témata, klíčové koncepty, větve a podvětve do standardní Markdown syntaxe pro vykreslení Markmap.js.

---
**Kontextové informace uživatele:**
Jméno uživatele: {user_name}
Aktuální datum a čas: {current_date_time_str}
Aktuální den v týdnu: {current_weekday}
Aktuální časová zóna: {current_timezone_str}
Jazyk uživatele: {user_language}
---

**Obsah dlouhého textu:**
{long_text_content}
"""

HTML_WRAPPER_TEMPLATE = """
<!-- OPENWEBUI_PLUGIN_OUTPUT -->
<!DOCTYPE html>
<html lang="{user_language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            margin: 0; 
            padding: 10px; 
            background-color: transparent; 
        }
        #main-container { 
            display: flex; 
            flex-direction: column; 
            gap: 20px; 
            align-items: stretch; 
            width: 100%;
        }
        .plugin-item { 
            width: 100%; 
            border-radius: 12px; 
            overflow: visible; 
            transition: all 0.3s ease;
        }
        .plugin-item:hover {
            transform: translateY(-2px);
        }
        /* STYLES_INSERTION_POINT */
    </style>
</head>
<body>
    <div id="main-container">
        <!-- CONTENT_INSERTION_POINT -->
    </div>
    <!-- SCRIPTS_INSERTION_POINT -->
</body>
</html>
"""

CSS_TEMPLATE_MINDMAP = """
        :root {
            --primary-color: #1e88e5;
            --secondary-color: #43a047;
            --background-color: #f4f6f8;
            --card-bg-color: #ffffff;
            --text-color: #000000;
            --link-color: #546e7a;
            --node-stroke-color: #90a4ae;
            --muted-text-color: #546e7a;
            --border-color: #e0e0e0;
            --header-gradient: linear-gradient(135deg, var(--secondary-color), var(--primary-color));
            --shadow: 0 10px 20px rgba(0, 0, 0, 0.06);
            --border-radius: 12px;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .theme-dark {
            --primary-color: #64b5f6;
            --secondary-color: #81c784;
            --background-color: #111827;
            --card-bg-color: #1f2937;
            --text-color: #ffffff;
            --link-color: #cbd5e1;
            --node-stroke-color: #94a3b8;
            --muted-text-color: #9ca3af;
            --border-color: #374151;
            --header-gradient: linear-gradient(135deg, #0ea5e9, #22c55e);
            --shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
        }
        .mindmap-container-wrapper {
            font-family: var(--font-family);
            line-height: 1.6;
            color: var(--text-color);
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            height: 100%;
            display: flex;
            flex-direction: column;
            background: var(--background-color);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
        }
        .header {
            background: var(--header-gradient);
            color: white;
            padding: 18px 20px;
            text-align: center;
            border-top-left-radius: var(--border-radius);
            border-top-right-radius: var(--border-radius);
        }
        .header h1 {
            margin: 0;
            font-size: 1.4em;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        .user-context {
            font-size: 0.85em;
            color: var(--muted-text-color);
            background-color: rgba(255, 255, 255, 0.6);
            padding: 8px 14px;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            border-bottom: 1px solid var(--border-color);
            gap: 6px;
        }
        .theme-dark .user-context {
            background-color: rgba(31, 41, 55, 0.7);
        }
        .user-context span { margin: 2px 6px; }
        .content-area {
            padding: 16px;
            flex-grow: 1;
            background: var(--card-bg-color);
        }
        .markmap-container {
            position: relative;
            background-color: var(--card-bg-color);
            border-radius: 10px;
            padding: 12px;
            display: flex;
            justify-content: center;
            align-items: center;
            border: 1px solid var(--border-color);
            width: 100%;
            min-height: 60vh;
            overflow: visible;
        }
        .markmap-container svg {
            width: 100%;
            height: 100%;
        }
        .markmap-container svg text {
            fill: var(--text-color) !important;
            font-family: var(--font-family);
        }
        .markmap-container svg foreignObject,
        .markmap-container svg .markmap-foreign,
        .markmap-container svg .markmap-foreign div {
            color: var(--text-color) !important;
            font-family: var(--font-family);
        }
        .markmap-container svg .markmap-link {
            stroke: var(--link-color) !important;
        }
        .markmap-container svg .markmap-node circle,
        .markmap-container svg .markmap-node rect {
            stroke: var(--node-stroke-color) !important;
        }
        .control-rows {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-top: 12px;
        }
        .btn-group {
            display: inline-flex;
            gap: 6px;
            align-items: center;
        }
        .control-btn {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.9em;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.15s ease, transform 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            height: 36px;
            box-sizing: border-box;
        }
        select.control-btn {
            appearance: none;
            padding-right: 28px;
            background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FFFFFF%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
            background-repeat: no-repeat;
            background-position: right 8px center;
            background-size: 10px;
        }
        .control-btn.secondary { background-color: var(--secondary-color); }
        .control-btn.neutral { background-color: #64748b; }
        .control-btn:hover { transform: translateY(-1px); }
        .control-btn.copied { background-color: #2e7d32; }
        .control-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .footer {
            text-align: center;
            padding: 12px;
            font-size: 0.85em;
            color: var(--muted-text-color);
            background-color: var(--card-bg-color);
            border-top: 1px solid var(--border-color);
            border-bottom-left-radius: var(--border-radius);
            border-bottom-right-radius: var(--border-radius);
        }

        .footer a {
            color: var(--primary-color);
            text-decoration: none;
            font-weight: 500;
        }
        .footer a:hover { text-decoration: underline; }
        .error-message {
            color: #c62828;
            background-color: #ffcdd2;
            border: 1px solid #ef9a9a;
            padding: 14px;
            border-radius: 8px;
            font-weight: 500;
            font-size: 1em;
        }
"""

CONTENT_TEMPLATE_MINDMAP = """
        <div class="mindmap-container-wrapper">
            <div class="header">
                <h1>🧠 Chytrá myšlenková mapa</h1>
            </div>
            <div class="user-context">
                <span><strong>Uživatel:</strong> {user_name}</span>
                <span><strong>Čas:</strong> {current_date_time_str}</span>
            </div>
            <div class="content-area">
                <div class="markmap-container" id="markmap-container-{unique_id}"></div>
                <div class="control-rows">
                    <div class="btn-group">
                        <button id="download-png-btn-{unique_id}" class="control-btn secondary">
                            <span class="btn-text">PNG</span>
                        </button>
                        <button id="download-svg-btn-{unique_id}" class="control-btn">
                            <span class="btn-text">SVG</span>
                        </button>
                        <button id="download-md-btn-{unique_id}" class="control-btn neutral">
                            <span class="btn-text">Markdown</span>
                        </button>
                    </div>
                    <div class="btn-group">
                        <button id="zoom-out-btn-{unique_id}" class="control-btn neutral" title="Oddálit">-</button>
                        <button id="zoom-reset-btn-{unique_id}" class="control-btn neutral" title="Resetovat">Reset</button>
                        <button id="zoom-in-btn-{unique_id}" class="control-btn neutral" title="Přiblížit">+</button>
                    </div>
                    <div class="btn-group">
                        <select id="depth-select-{unique_id}" class="control-btn secondary" title="Úroveň rozbalení">
                            <option value="0" selected>Rozbalit vše</option>
                            <option value="2">Úroveň 2</option>
                            <option value="3">Úroveň 3</option>
                        </select>
                        <button id="fullscreen-btn-{unique_id}" class="control-btn">Celá obrazovka</button>
                        <button id="theme-toggle-btn-{unique_id}" class="control-btn neutral">Motiv</button>
                    </div>
                </div>
            </div>
            <div class="footer">
                <p>© {current_year} Chytrá myšlenková mapa • <a href="https://markmap.js.org/" target="_blank">Markmap</a></p>
            </div>
        </div>
        
        <script type="text/template" id="markdown-source-{unique_id}">{markdown_syntax}</script>
"""

SCRIPT_TEMPLATE_MINDMAP = """
    <script>
      (function() {
        const uniqueId = "{unique_id}";

        const loadScriptOnce = (src, checkFn) => {
            if (checkFn()) return Promise.resolve();
            return new Promise((resolve, reject) => {
                const existing = document.querySelector(`script[data-src="${src}"]`);
                if (existing) {
                    existing.addEventListener('load', () => resolve());
                    existing.addEventListener('error', () => reject(new Error('Načítání selhalo: ' + src)));
                    return;
                }
                const script = document.createElement('script');
                script.src = src;
                script.async = true;
                script.dataset.src = src;
                script.onload = () => resolve();
                script.onerror = () => reject(new Error('Načítání selhalo: ' + src));
                document.head.appendChild(script);
            });
        };

        const ensureMarkmapReady = () =>
            loadScriptOnce('https://cdn.jsdelivr.net/npm/d3@7', () => window.d3)
                .then(() => loadScriptOnce('https://cdn.jsdelivr.net/npm/markmap-lib@0.17', () => window.markmap && window.markmap.Transformer))
                .then(() => loadScriptOnce('https://cdn.jsdelivr.net/npm/markmap-view@0.17', () => window.markmap && window.markmap.Markmap));

        const parseColorLuma = (colorStr) => {
            if (!colorStr) return null;
            // hex #rrggbb or rrggbb
            let m = colorStr.match(/^#?([0-9a-f]{6})$/i);
            if (m) {
                const hex = m[1];
                const r = parseInt(hex.slice(0, 2), 16);
                const g = parseInt(hex.slice(2, 4), 16);
                const b = parseInt(hex.slice(4, 6), 16);
                return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
            }
            // rgb(r, g, b) or rgba(r, g, b, a)
            m = colorStr.match(/rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
            if (m) {
                const r = parseInt(m[1], 10);
                const g = parseInt(m[2], 10);
                const b = parseInt(m[3], 10);
                return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
            }
            return null;
        };

        const getThemeFromMeta = (doc, scope = 'self') => {
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
            } catch (err) {
                return null;
            }
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
            } catch (err) {
                return null;
            }
        };

        const setTheme = (wrapperEl, explicitTheme) => {
            const parentDoc = getParentDocumentSafe();
            const metaThemeParent = parentDoc ? getThemeFromMeta(parentDoc, 'parent') : null;
            const parentClassTheme = getThemeFromParentClass();
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            const chosen = explicitTheme || metaThemeParent || parentClassTheme || (prefersDark ? 'dark' : 'light');
            wrapperEl.classList.toggle('theme-dark', chosen === 'dark');
            return chosen;
        };

        const renderMindmap = () => {
            const containerEl = document.getElementById('markmap-container-' + uniqueId);
            if (!containerEl || containerEl.dataset.markmapRendered) return;

            const sourceEl = document.getElementById('markdown-source-' + uniqueId);
            if (!sourceEl) return;

            const markdownContent = sourceEl.textContent.trim();
            if (!markdownContent) {
                containerEl.innerHTML = '<div class=\"error-message\">⚠️ Nelze načíst myšlenkovou mapu: Chybí platný obsah.</div>';
                return;
            }

            ensureMarkmapReady().then(() => {
                const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svgEl.style.width = '100%';
                svgEl.style.height = '100%';
                svgEl.style.minHeight = '60vh';
                containerEl.innerHTML = '';
                containerEl.appendChild(svgEl);

                const { Transformer, Markmap } = window.markmap;
                const transformer = new Transformer();
                const { root } = transformer.transform(markdownContent);

                const style = (id) => `
                    ${id} text, ${id} foreignObject { font-size: 14px; }
                    ${id} foreignObject h1 { font-size: 22px; font-weight: 700; margin: 0; }
                    ${id} foreignObject h2 { font-size: 18px; font-weight: 600; margin: 0; }
                    ${id} foreignObject strong { font-weight: 700; }
                `;
                const options = {
                    autoFit: true,
                    style: style,
                    initialExpandLevel: Infinity,
                    zoom: true,
                    pan: true
                };

                const markmapInstance = Markmap.create(svgEl, options, root);
                containerEl.dataset.markmapRendered = 'true';

                setupControls({
                    containerEl,
                    svgEl,
                    markmapInstance,
                    root,
                });

            }).catch((error) => {
                console.error('Chyba načítání Markmap:', error);
                containerEl.innerHTML = '<div class=\"error-message\">⚠️ Načítání zdrojů selhalo, zkuste to prosím později.</div>';
            });
        };

        const setupControls = ({ containerEl, svgEl, markmapInstance, root }) => {
            const downloadSvgBtn = document.getElementById('download-svg-btn-' + uniqueId);
            const downloadPngBtn = document.getElementById('download-png-btn-' + uniqueId);
            const downloadMdBtn = document.getElementById('download-md-btn-' + uniqueId);
            const zoomInBtn = document.getElementById('zoom-in-btn-' + uniqueId);
            const zoomOutBtn = document.getElementById('zoom-out-btn-' + uniqueId);
            const zoomResetBtn = document.getElementById('zoom-reset-btn-' + uniqueId);
            const depthSelect = document.getElementById('depth-select-' + uniqueId);
            const fullscreenBtn = document.getElementById('fullscreen-btn-' + uniqueId);
            const themeToggleBtn = document.getElementById('theme-toggle-btn-' + uniqueId);

            const wrapper = containerEl.closest('.mindmap-container-wrapper');
            let currentTheme = setTheme(wrapper);

            const showFeedback = (button, textOk = 'Hotovo', textFail = 'Selhalo') => {
                if (!button) return;
                const buttonText = button.querySelector('.btn-text') || button;
                const originalText = buttonText.textContent;
                button.disabled = true;
                buttonText.textContent = textOk;
                button.classList.add('copied');
                setTimeout(() => {
                    buttonText.textContent = originalText;
                    button.disabled = false;
                    button.classList.remove('copied');
                }, 1800);
            };

            const copyToClipboard = (content, button) => {
                if (navigator.clipboard && window.isSecureContext) {
                    navigator.clipboard.writeText(content).then(() => showFeedback(button), () => showFeedback(button, 'Selhalo', 'Selhalo'));
                } else {
                    const textArea = document.createElement('textarea');
                    textArea.value = content;
                    textArea.style.position = 'fixed';
                    textArea.style.opacity = '0';
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    try {
                        document.execCommand('copy');
                        showFeedback(button);
                    } catch (err) {
                        showFeedback(button, 'Selhalo', 'Selhalo');
                    }
                    document.body.removeChild(textArea);
                }
            };

            const handleDownloadSVG = () => {
                const svg = containerEl.querySelector('svg');
                if (!svg) return;
                // Inline styles before export
                const clonedSvg = svg.cloneNode(true);
                const style = document.createElement('style');
                style.textContent = `
                    text { font-family: sans-serif; fill: ${currentTheme === 'dark' ? '#ffffff' : '#000000'}; }
                    foreignObject, .markmap-foreign, .markmap-foreign div { color: ${currentTheme === 'dark' ? '#ffffff' : '#000000'}; font-family: sans-serif; font-size: 14px; }
                    h1 { font-size: 22px; font-weight: 700; margin: 0; }
                    h2 { font-size: 18px; font-weight: 600; margin: 0; }
                    strong { font-weight: 700; }
                    .markmap-link { stroke: ${currentTheme === 'dark' ? '#cbd5e1' : '#546e7a'}; }
                    .markmap-node circle, .markmap-node rect { stroke: ${currentTheme === 'dark' ? '#94a3b8' : '#94a3b8'}; }
                `;
                clonedSvg.prepend(style);
                const svgData = new XMLSerializer().serializeToString(clonedSvg);
                copyToClipboard(svgData, downloadSvgBtn);
            };

            const handleDownloadMD = () => {
                const markdownContent = document.getElementById('markdown-source-' + uniqueId)?.textContent || '';
                if (!markdownContent) return;
                copyToClipboard(markdownContent, downloadMdBtn);
            };

            const handleDownloadPNG = () => {
                const btn = downloadPngBtn;
                const originalText = btn.querySelector('.btn-text').textContent;
                btn.querySelector('.btn-text').textContent = 'Generuji...';
                btn.disabled = true;

                const svg = containerEl.querySelector('svg');
                if (!svg) {
                    btn.querySelector('.btn-text').textContent = originalText;
                    btn.disabled = false;
                    showFeedback(btn, 'Selhalo', 'Selhalo');
                    return;
                }

                try {
                    // Clone SVG and inline styles
                    const clonedSvg = svg.cloneNode(true);
                    clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                    clonedSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
                    
                    const rect = svg.getBoundingClientRect();
                    const width = rect.width || 800;
                    const height = rect.height || 600;
                    clonedSvg.setAttribute('width', width);
                    clonedSvg.setAttribute('height', height);

                    // Remove foreignObject (HTML content) and replace with text
                    const foreignObjects = clonedSvg.querySelectorAll('foreignObject');
                    foreignObjects.forEach(fo => {
                        const text = fo.textContent || '';
                        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                        const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        textEl.setAttribute('x', fo.getAttribute('x') || '0');
                        textEl.setAttribute('y', (parseFloat(fo.getAttribute('y') || '0') + 14).toString());
                        textEl.setAttribute('fill', currentTheme === 'dark' ? '#ffffff' : '#000000');
                        textEl.setAttribute('font-family', 'sans-serif');
                        textEl.setAttribute('font-size', '14');
                        textEl.textContent = text.trim();
                        g.appendChild(textEl);
                        fo.parentNode.replaceChild(g, fo);
                    });

                    // Inline styles
                    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
                    style.textContent = `
                        text { font-family: sans-serif; font-size: 14px; fill: ${currentTheme === 'dark' ? '#ffffff' : '#000000'}; }
                        .markmap-link { fill: none; stroke: ${currentTheme === 'dark' ? '#cbd5e1' : '#546e7a'}; stroke-width: 2; }
                        .markmap-node circle { stroke: ${currentTheme === 'dark' ? '#94a3b8' : '#94a3b8'}; stroke-width: 2; }
                    `;
                    clonedSvg.insertBefore(style, clonedSvg.firstChild);

                    // Add background rect
                    const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    bgRect.setAttribute('width', '100%');
                    bgRect.setAttribute('height', '100%');
                    bgRect.setAttribute('fill', currentTheme === 'dark' ? '#1f2937' : '#ffffff');
                    clonedSvg.insertBefore(bgRect, clonedSvg.firstChild);

                    const svgData = new XMLSerializer().serializeToString(clonedSvg);
                    const svgBase64 = btoa(unescape(encodeURIComponent(svgData)));
                    const dataUrl = 'data:image/svg+xml;base64,' + svgBase64;

                    const img = new Image();
                    img.onload = () => {
                        const canvas = document.createElement('canvas');
                        const scale = 9;
                        canvas.width = width * scale;
                        canvas.height = height * scale;
                        const ctx = canvas.getContext('2d');
                        ctx.scale(scale, scale);
                        ctx.fillStyle = currentTheme === 'dark' ? '#1f2937' : '#ffffff';
                        ctx.fillRect(0, 0, width, height);
                        ctx.drawImage(img, 0, 0, width, height);

                        canvas.toBlob((blob) => {
                            if (!blob) {
                                btn.querySelector('.btn-text').textContent = originalText;
                                btn.disabled = false;
                                showFeedback(btn, 'Selhalo', 'Selhalo');
                                return;
                            }
                            
                            // Use non-bubbling MouseEvent to avoid router interception
                            const a = document.createElement('a');
                            a.download = 'myslenkova-mapa.png';
                            a.href = URL.createObjectURL(blob);
                            a.style.display = 'none';
                            document.body.appendChild(a);
                            
                            const evt = new MouseEvent('click', {
                                view: window,
                                bubbles: false,
                                cancelable: false
                            });
                            a.dispatchEvent(evt);
                            
                            setTimeout(() => {
                                document.body.removeChild(a);
                                URL.revokeObjectURL(a.href);
                            }, 100);

                            btn.querySelector('.btn-text').textContent = originalText;
                            btn.disabled = false;
                            showFeedback(btn);
                        }, 'image/png');
                    };
                    
                    img.onerror = (e) => {
                        console.error('Chyba načítání PNG obrázku:', e);
                        btn.querySelector('.btn-text').textContent = originalText;
                        btn.disabled = false;
                        showFeedback(btn, 'Selhalo', 'Selhalo');
                    };
                    
                    img.src = dataUrl;
                } catch (err) {
                    console.error('Chyba exportu PNG:', err);
                    btn.querySelector('.btn-text').textContent = originalText;
                    btn.disabled = false;
                    showFeedback(btn, 'Selhalo', 'Selhalo');
                }
            };

            const handleZoom = (direction) => {
                if (direction === 'reset') {
                    markmapInstance.fit();
                    return;
                }
                // Simple zoom simulation if d3 zoom instance is not accessible
                // Markmap uses d3-zoom, so we can try to select the svg and transition
                const svg = d3.select(svgEl);
                // We can't easily access the internal zoom behavior object created by markmap
                // So we rely on fit() for reset, and maybe just let user scroll/pinch for zoom
                // Or we can try to rescale if supported
                if (markmapInstance.rescale) {
                    const scale = direction === 'in' ? 1.25 : 0.8;
                    markmapInstance.rescale(scale);
                } else {
                    // Fallback: just fit, as manual transform manipulation conflicts with d3
                    // Or we could try to find the zoom behavior attached to the node
                    // const zoom = d3.zoomTransform(svgEl);
                    // But we need the zoom behavior function to call scaleBy
                }
            };

            const handleDepthChange = (e) => {
                const level = parseInt(e.target.value, 10);
                const expandLevel = level === 0 ? Infinity : level;
                
                // Deep clone root to reset internal state (payload.fold) added by markmap
                const cleanRoot = JSON.parse(JSON.stringify(root));
                
                markmapInstance.setOptions({ initialExpandLevel: expandLevel });
                markmapInstance.setData(cleanRoot);
                markmapInstance.fit();
            };

            const handleFullscreen = () => {
                const el = containerEl;
                if (!document.fullscreenElement) {
                    el.requestFullscreen().then(() => {
                        setTimeout(() => markmapInstance.fit(), 200);
                    });
                } else {
                    document.exitFullscreen();
                }
            };
            
            document.addEventListener('fullscreenchange', () => {
                if (document.fullscreenElement === containerEl) {
                    setTimeout(() => markmapInstance.fit(), 200);
                }
            });

            const handleThemeToggle = () => {
                currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
                setTheme(wrapper, currentTheme);
            };

            downloadSvgBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleDownloadSVG(); });
            downloadMdBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleDownloadMD(); });
            downloadPngBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleDownloadPNG(); });
            zoomInBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleZoom('in'); });
            zoomOutBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleZoom('out'); });
            zoomResetBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleZoom('reset'); });
            depthSelect?.addEventListener('change', (e) => { e.stopPropagation(); handleDepthChange(e); });
            fullscreenBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleFullscreen(); });
            themeToggleBtn?.addEventListener('click', (e) => { e.stopPropagation(); handleThemeToggle(); });
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', renderMindmap);
        } else {
            renderMindmap();
        }
      })();
    </script>
"""


class Action:
    class Valves(BaseModel):
        SHOW_STATUS: bool = Field(
            default=True,
            description="Zda zobrazovat průběh akce v rozhraní chatu.",
        )
        MODEL_ID: str = Field(
            default="",
            description="ID interního LLM modelu pro analýzu textu. Pokud je prázdné, použije se model aktuální konverzace.",
        )
        MIN_TEXT_LENGTH: int = Field(
            default=100,
            description="Minimální délka textu (počet znaků) požadovaná pro analýzu myšlenkové mapy.",
        )
        CLEAR_PREVIOUS_HTML: bool = Field(
            default=False,
            description="Zda vynutit smazání předchozích výstupů pluginu (pokud True, přepíše místo slučování).",
        )
        MESSAGE_COUNT: int = Field(
            default=1,
            description="Počet posledních zpráv pro generování. Nastavte na 1 pro jen poslední zprávu, nebo vyšší pro více kontextu.",
        )
        OUTPUT_MODE: str = Field(
            default="html",
            description="Režim výstupu: 'html' pro interaktivní HTML (výchozí), nebo 'image' pro vložení jako Markdown obrázek.",
        )
        SHOW_DEBUG_LOG: bool = Field(
            default=False,
            description="Zda tisknout debug logy v konzoli prohlížeče.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.weekday_map = {
            "Monday": "Pondělí",
            "Tuesday": "Úterý",
            "Wednesday": "Středa",
            "Thursday": "Čtvrtek",
            "Friday": "Pátek",
            "Saturday": "Sobota",
            "Sunday": "Neděle",
        }

    def _get_user_context(self, __user__: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Získá základní kontext uživatele s bezpečnými výchozími hodnotami."""
        if isinstance(__user__, (list, tuple)):
            user_data = __user__[0] if __user__ else {}
        elif isinstance(__user__, dict):
            user_data = __user__
        else:
            user_data = {}

        return {
            "user_id": user_data.get("id", "unknown_user"),
            "user_name": user_data.get("name", "Uživatel"),
            "user_language": user_data.get("language", "cs-CZ"),
        }

    def _get_chat_context(
        self, body: dict, __metadata__: Optional[dict] = None
    ) -> Dict[str, str]:
        """
        Jednotné získání kontextu chatu (chat_id, message_id).
        Upřednostňuje získání z body, poté z metadata.
        """
        chat_id = ""
        message_id = ""

        # 1. Zkus získat z body
        if isinstance(body, dict):
            chat_id = body.get("chat_id", "")
            message_id = body.get("id", "")  # message_id je obvykle 'id' v body

            # Zkontroluj body.metadata jako zálohu
            if not chat_id or not message_id:
                body_metadata = body.get("metadata", {})
                if isinstance(body_metadata, dict):
                    if not chat_id:
                        chat_id = body_metadata.get("chat_id", "")
                    if not message_id:
                        message_id = body_metadata.get("message_id", "")

        # 2. Zkus získat z __metadata__ (jako doplněk)
        if __metadata__ and isinstance(__metadata__, dict):
            if not chat_id:
                chat_id = __metadata__.get("chat_id", "")
            if not message_id:
                message_id = __metadata__.get("message_id", "")

        return {
            "chat_id": str(chat_id).strip(),
            "message_id": str(message_id).strip(),
        }

    def _extract_markdown_syntax(self, llm_output: str) -> str:
        match = re.search(r"```markdown\s*(.*?)\s*```", llm_output, re.DOTALL)
        if match:
            extracted_content = match.group(1).strip()
        else:
            logger.warning(
                "Výstup LLM striktně nesledoval očekávaný Markdown formát, celý výstup je považován za shrnutí."
            )
            extracted_content = llm_output.strip()
        return extracted_content.replace("</script>", "<\\/script>")

    async def _emit_status(self, emitter, description: str, done: bool = False):
        """Emituje událost aktualizace stavu."""
        if self.valves.SHOW_STATUS and emitter:
            await emitter(
                {"type": "status", "data": {"description": description, "done": done}}
            )

    async def _emit_notification(self, emitter, content: str, ntype: str = "info"):
        """Emituje událost notifikace (info/success/warning/error)."""
        if emitter:
            await emitter(
                {"type": "notification", "data": {"type": ntype, "content": content}}
            )

    async def _emit_debug_log(self, emitter, title: str, data: dict):
        """Tiskne strukturované debug logy v konzoli prohlížeče"""
        if not self.valves.SHOW_DEBUG_LOG or not emitter:
            return

        try:
            js_code = f"""
                (async function() {{
                    console.group("🛠️ {title}");
                    console.log({json.dumps(data, ensure_ascii=False)});
                    console.groupEnd();
                }})();
            """

            await emitter({"type": "execute", "data": {"code": js_code}})
        except Exception as e:
            print(f"Chyba při emitování debug logu: {e}")

    async def _emit_debug_log(self, emitter, title: str, data: dict):
        """Tiskne strukturované debug logy v konzoli prohlížeče"""
        if not self.valves.SHOW_DEBUG_LOG or not emitter:
            return

        try:
            js_code = f"""
                (async function() {{
                    console.group("🛠️ {title}");
                    console.log({json.dumps(data, ensure_ascii=False)});
                    console.groupEnd();
                }})();
            """

            await emitter({"type": "execute", "data": {"code": js_code}})
        except Exception as e:
            print(f"Chyba při emitování debug logu: {e}")

    def _remove_existing_html(self, content: str) -> str:
        """Odstraní existující HTML bloky generované pluginem z obsahu."""
        pattern = r"```html\s*<!-- OPENWEBUI_PLUGIN_OUTPUT -->[\s\S]*?```"
        return re.sub(pattern, "", content).strip()

    def _extract_text_content(self, content) -> str:
        """Extrahuje text z obsahu zprávy, podporuje multimodální formáty zpráv"""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Multimodální zpráva: [{"type": "text", "text": "..."}, {"type": "image_url", ...}]
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
        existing_html_code: str,
        new_content: str,
        new_styles: str = "",
        new_scripts: str = "",
        user_language: str = "cs-CZ",
    ) -> str:
        """
        Sloučí nový obsah do existujícího HTML kontejneru, nebo vytvoří nový.
        """
        if (
            "<!-- OPENWEBUI_PLUGIN_OUTPUT -->" in existing_html_code
            and "<!-- CONTENT_INSERTION_POINT -->" in existing_html_code
        ):
            base_html = existing_html_code
            base_html = re.sub(r"^```html\s*", "", base_html)
            base_html = re.sub(r"\s*```$", "", base_html)
        else:
            base_html = HTML_WRAPPER_TEMPLATE.replace("{user_language}", user_language)

        wrapped_content = f'<div class="plugin-item">\n{new_content}\n</div>'

        if new_styles:
            base_html = base_html.replace(
                "/* STYLES_INSERTION_POINT */",
                f"{new_styles}\n/* STYLES_INSERTION_POINT */",
            )

        base_html = base_html.replace(
            "<!-- CONTENT_INSERTION_POINT -->",
            f"{wrapped_content}\n<!-- CONTENT_INSERTION_POINT -->",
        )

        if new_scripts:
            base_html = base_html.replace(
                "<!-- SCRIPTS_INSERTION_POINT -->",
                f"{new_scripts}\n<!-- SCRIPTS_INSERTION_POINT -->",
            )

        return base_html.strip()

    def _generate_image_js_code(
        self,
        unique_id: str,
        chat_id: str,
        message_id: str,
        markdown_syntax: str,
    ) -> str:
        """Generuje JavaScript kód pro vykreslení SVG na frontendu a vložení obrázku"""

        # Escapování syntaxe pro vložení do JS
        syntax_escaped = (
            markdown_syntax.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
            .replace("</script>", "<\\/script>")
        )

        return f"""
(async function() {{
    const uniqueId = "{unique_id}";
    const chatId = "{chat_id}";
    const messageId = "{message_id}";
    const defaultWidth = 1200;
    const defaultHeight = 800;
    
    // Detekce motivu - kontrola nadřazeného dokumentu pro OpenWebUI motiv
    const detectTheme = () => {{
        try {{
            // 1. Kontrola třídy html/body nadřazeného dokumentu nebo data-theme
            const html = document.documentElement;
            const body = document.body;
            const htmlClass = html ? html.className : '';
            const bodyClass = body ? body.className : '';
            const htmlDataTheme = html ? html.getAttribute('data-theme') : '';
            
            if (htmlDataTheme === 'dark' || bodyClass.includes('dark') || htmlClass.includes('dark')) {{
                return 'dark';
            }}
            if (htmlDataTheme === 'light' || bodyClass.includes('light') || htmlClass.includes('light')) {{
                return 'light';
            }}
            
            // 2. Kontrola meta theme-color
            const metas = document.querySelectorAll('meta[name="theme-color"]');
            if (metas.length > 0) {{
                const color = metas[metas.length - 1].content.trim();
                const m = color.match(/^#?([0-9a-f]{{6}})$/i);
                if (m) {{
                    const hex = m[1];
                    const r = parseInt(hex.slice(0, 2), 16);
                    const g = parseInt(hex.slice(2, 4), 16);
                    const b = parseInt(hex.slice(4, 6), 16);
                    const luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
                    return luma < 0.5 ? 'dark' : 'light';
                }}
            }}
            
            // 3. Kontrola systémové preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {{
                return 'dark';
            }}
            
            return 'light';
        }} catch (e) {{
            return 'light';
        }}
    }};
    
    const currentTheme = detectTheme();
    console.log("[MindMap Image] Detekovaný motiv:", currentTheme);
    
    // Barvy založené na motivu
    const colors = currentTheme === 'dark' ? {{
        background: '#1f2937',
        text: '#e5e7eb',
        link: '#94a3b8',
        nodeStroke: '#64748b'
    }} : {{
        background: '#ffffff',
        text: '#1f2937',
        link: '#546e7a',
        nodeStroke: '#94a3b8'
    }};
    
    // Auto-detekce šířky kontejneru chatu pro responzivní velikost
    let svgWidth = defaultWidth;
    let svgHeight = defaultHeight;
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {{
        const containerWidth = chatContainer.clientWidth;
        if (containerWidth > 100) {{
            // Použití šířky kontejneru s paddingem (90% kontejneru)
            svgWidth = Math.floor(containerWidth * 0.9);
            // Zachování poměru stran založeného na výchozích rozměrech
            svgHeight = Math.floor(svgWidth * (defaultHeight / defaultWidth));
            console.log("[MindMap Image] Auto-detekovaná šířka kontejneru:", containerWidth, "-> SVG:", svgWidth, "x", svgHeight);
        }}
    }}
    
    console.log("[MindMap Image] Zahájení vykreslování...");
    console.log("[MindMap Image] chatId:", chatId, "messageId:", messageId);
    
    try {{
        // Načtení D3 pokud není načteno
        if (typeof d3 === 'undefined') {{
            console.log("[MindMap Image] Načítání D3...");
            await new Promise((resolve, reject) => {{
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/d3@7';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            }});
        }}
        
        // Načtení markmap-lib pokud není načteno
        if (!window.markmap || !window.markmap.Transformer) {{
            console.log("[MindMap Image] Načítání markmap-lib...");
            await new Promise((resolve, reject) => {{
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/markmap-lib@0.17';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            }});
        }}
        
        // Načtení markmap-view pokud není načteno
        if (!window.markmap || !window.markmap.Markmap) {{
            console.log("[MindMap Image] Načítání markmap-view...");
            await new Promise((resolve, reject) => {{
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/markmap-view@0.17';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            }});
        }}
        
        const {{ Transformer, Markmap }} = window.markmap;
        
        // Získání markdown syntaxe
        let syntaxContent = `{syntax_escaped}`;
        console.log("[MindMap Image] Délka syntaxe:", syntaxContent.length);
        
        // Vytvoření offscreen kontejneru
        const container = document.createElement('div');
        container.id = 'mindmap-offscreen-' + uniqueId;
        container.style.cssText = 'position:absolute;left:-9999px;top:-9999px;width:' + svgWidth + 'px;height:' + svgHeight + 'px;';
        document.body.appendChild(container);
        
        // Vytvoření SVG elementu
        const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgEl.setAttribute('width', svgWidth);
        svgEl.setAttribute('height', svgHeight);
        svgEl.style.width = svgWidth + 'px';
        svgEl.style.height = svgHeight + 'px';
        svgEl.style.backgroundColor = colors.background;
        container.appendChild(svgEl);
        
        // Transformace markdown na strom
        const transformer = new Transformer();
        const {{ root }} = transformer.transform(syntaxContent);
        
        // Vytvoření instance markmap
        const options = {{
            autoFit: true,
            initialExpandLevel: Infinity,
            zoom: false,
            pan: false
        }};
        
        console.log("[MindMap Image] Vykreslování markmap...");
        const markmapInstance = Markmap.create(svgEl, options, root);
        
        // Čekání na dokončení vykreslení
        await new Promise(resolve => setTimeout(resolve, 1500));
        markmapInstance.fit();
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Klonování a příprava SVG pro export
        const clonedSvg = svgEl.cloneNode(true);
        clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        clonedSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
        
        // Přidání obdélníku pozadí s barvou motivu
        const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bgRect.setAttribute('width', '100%');
        bgRect.setAttribute('height', '100%');
        bgRect.setAttribute('fill', colors.background);
        clonedSvg.insertBefore(bgRect, clonedSvg.firstChild);
        
        // Přidání inline stylů s barvami motivu
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        style.textContent = `
            text {{ font-family: sans-serif; font-size: 14px; fill: ${{colors.text}}; }}
            foreignObject, .markmap-foreign, .markmap-foreign div {{ color: ${{colors.text}}; font-family: sans-serif; font-size: 14px; }}
            h1 {{ font-size: 22px; font-weight: 700; margin: 0; }}
            h2 {{ font-size: 18px; font-weight: 600; margin: 0; }}
            strong {{ font-weight: 700; }}
            .markmap-link {{ stroke: ${{colors.link}}; fill: none; }}
            .markmap-node circle, .markmap-node rect {{ stroke: ${{colors.nodeStroke}}; }}
        `;
        clonedSvg.insertBefore(style, bgRect.nextSibling);
        
        // Konverze foreignObject na text pro lepší kompatibilitu
        const foreignObjects = clonedSvg.querySelectorAll('foreignObject');
        foreignObjects.forEach(fo => {{
            const text = fo.textContent || '';
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            textEl.setAttribute('x', fo.getAttribute('x') || '0');
            textEl.setAttribute('y', (parseFloat(fo.getAttribute('y') || '0') + 14).toString());
            textEl.setAttribute('fill', colors.text);
            textEl.setAttribute('font-family', 'sans-serif');
            textEl.setAttribute('font-size', '14');
            textEl.textContent = text.trim();
            g.appendChild(textEl);
            fo.parentNode.replaceChild(g, fo);
        }});
        
        // Serializace SVG do stringu
        const svgData = new XMLSerializer().serializeToString(clonedSvg);
        
        // Úklid kontejneru
        document.body.removeChild(container);
        
        // Konverze SVG stringu na Blob
        const blob = new Blob([svgData], {{ type: 'image/svg+xml' }});
        const file = new File([blob], `myslenkova-mapa-${{uniqueId}}.svg`, {{ type: 'image/svg+xml' }});
        
        // Nahrání souboru do OpenWebUI API
        console.log("[MindMap Image] Nahrávání SVG souboru...");
        const token = localStorage.getItem("token");
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch('/api/v1/files/', {{
            method: 'POST',
            headers: {{
                'Authorization': `Bearer ${{token}}`
            }},
            body: formData
        }});
        
        if (!uploadResponse.ok) {{
            throw new Error(`Nahrávání selhalo: ${{uploadResponse.statusText}}`);
        }}
        
        const fileData = await uploadResponse.json();
        const fileId = fileData.id;
        const imageUrl = `/api/v1/files/${{fileId}}/content`;
        
        console.log("[MindMap Image] Soubor nahrán, ID:", fileId);
        
        // Generování markdown obrázku s URL souboru
        const markdownImage = `![🧠 Myšlenková mapa](${{imageUrl}})`;
        
        // Aktualizace zprávy přes API
        if (chatId && messageId) {{
            
            // Pomocná funkce s logikou opakování
            const fetchWithRetry = async (url, options, retries = 3) => {{
                for (let i = 0; i < retries; i++) {{
                    try {{
                        const response = await fetch(url, options);
                        if (response.ok) return response;
                        if (i < retries - 1) {{
                            console.log(`[MindMap Image] Pokus ${{i + 1}}/${{retries}} pro ${{url}}`);
                            await new Promise(r => setTimeout(r, 1000 * (i + 1)));
                        }}
                    }} catch (e) {{
                        if (i === retries - 1) throw e;
                        await new Promise(r => setTimeout(r, 1000 * (i + 1)));
                    }}
                }}
                return null;
            }};
            
            // Získání aktuálních dat chatu
            const getResponse = await fetch(`/api/v1/chats/${{chatId}}`, {{
                method: "GET",
                headers: {{ "Authorization": `Bearer ${{token}}` }}
            }});
            
            if (!getResponse.ok) {{
                throw new Error("Nepodařilo se získat data chatu: " + getResponse.status);
            }}
            
            const chatData = await getResponse.json();
            let updatedMessages = [];
            let newContent = "";
            
            if (chatData.chat && chatData.chat.messages) {{
                updatedMessages = chatData.chat.messages.map(m => {{
                    if (m.id === messageId) {{
                        const originalContent = m.content || "";
                        // Odstranění existujících obrázků myšlenkové mapy (jak base64 tak file URL vzory)
                        const mindmapPattern = /\\n*!\\[🧠[^\\]]*\\]\\((?:data:image\\/[^)]+|(?:\\/api\\/v1\\/files\\/[^)]+))\\)/g;
                        let cleanedContent = originalContent.replace(mindmapPattern, "");
                        cleanedContent = cleanedContent.replace(/\\n{{3,}}/g, "\\n\\n").trim();
                        // Přidání nového obrázku
                        newContent = cleanedContent + "\\n\\n" + markdownImage;
                        
                        // Kritické: Aktualizace obsahu jak v poli zpráv TAK v objektu history
                        // Objekt history je zdrojem pravdy pro databázi
                        if (chatData.chat.history && chatData.chat.history.messages) {{
                            if (chatData.chat.history.messages[messageId]) {{
                                chatData.chat.history.messages[messageId].content = newContent;
                            }}
                        }}
                        
                        return {{ ...m, content: newContent }};
                    }}
                    return m;
                }});
            }}
            
            if (!newContent) {{
                console.warn("[MindMap Image] Nepodařilo se najít zprávu k aktualizaci");
                return;
            }}
            
            // Pokus o aktualizaci frontendu přes event API (volitelné, nemusí existovat ve všech verzích)
            try {{
                await fetch(`/api/v1/chats/${{chatId}}/messages/${{messageId}}/event`, {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${{token}}`
                    }},
                    body: JSON.stringify({{
                        type: "chat:message",
                        data: {{ content: newContent }}
                    }})
                }});
            }} catch (eventErr) {{
                // Event API je volitelné, pokračovat s persistencí
                console.log("[MindMap Image] Event API není dostupné, pokračuji...");
            }}
            
            // Persistence do databáze aktualizací celého objektu chatu
            // Toto následuje tok API řízeného backendem OpenWebUI
            const updatePayload = {{
                chat: {{
                    ...chatData.chat,
                    messages: updatedMessages
                    // history je již aktualizováno na místě výše
                }}
            }};
            
            const persistResponse = await fetchWithRetry(`/api/v1/chats/${{chatId}}`, {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${{token}}`
                }},
                body: JSON.stringify(updatePayload)
            }});
            
            if (persistResponse && persistResponse.ok) {{
                console.log("[MindMap Image] ✅ Zpráva úspěšně uložena!");
            }} else {{
                console.error("[MindMap Image] ❌ Nepodařilo se uložit zprávu po opakovaných pokusech");
            }}
        }} else {{
            console.warn("[MindMap Image] ⚠️ Chybí chatId nebo messageId, nelze uložit");
        }}
        
    }} catch (error) {{
        console.error("[MindMap Image] Chyba:", error);
    }}
}})();
"""

    async def action(
        self,
        body: dict,
        __user__: Optional[Dict[str, Any]] = None,
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Callable[[Any], Awaitable[None]]] = None,
        __metadata__: Optional[dict] = None,
        __request__: Optional[Request] = None,
    ) -> Optional[dict]:
        logger.info("Action: Chytrá myšlenková mapa (v0.9.1) spuštěna")
        user_ctx = self._get_user_context(__user__)
        user_language = user_ctx["user_language"]
        user_name = user_ctx["user_name"]
        user_id = user_ctx["user_id"]

        try:
            tz_env = os.environ.get("TZ")
            tzinfo = ZoneInfo(tz_env) if tz_env else None
            now_dt = datetime.now(tzinfo or timezone.utc)
            current_date_time_str = now_dt.strftime("%d. %B %Y %H:%M:%S")
            current_weekday_en = now_dt.strftime("%A")
            current_weekday_zh = self.weekday_map.get(current_weekday_en, "Neznámý")
            current_year = now_dt.strftime("%Y")
            current_timezone_str = tz_env or "UTC"
        except Exception as e:
            logger.warning(f"Nepodařilo se získat informace o časové zóně: {e}, používám výchozí hodnoty.")
            now = datetime.now()
            current_date_time_str = now.strftime("%d. %B %Y %H:%M:%S")
            current_weekday_zh = "Neznámý"
            current_year = now.strftime("%Y")
            current_timezone_str = "Neznámá"

        await self._emit_notification(
            __event_emitter__,
            "Chytrá myšlenková mapa se spouští, generuji pro vás myšlenkovou mapu...",
            "info",
        )

        messages = body.get("messages")
        if not messages or not isinstance(messages, list):
            error_message = "Nelze získat platný obsah uživatelské zprávy."
            await self._emit_notification(__event_emitter__, error_message, "error")
            return {
                "messages": [{"role": "assistant", "content": f"❌ {error_message}"}]
            }

        # Získání posledních N zpráv na základě MESSAGE_COUNT
        message_count = min(self.valves.MESSAGE_COUNT, len(messages))
        recent_messages = messages[-message_count:]

        # Agregace obsahu z vybraných zpráv s popisky
        aggregated_parts = []
        for i, msg in enumerate(recent_messages, 1):
            text_content = self._extract_text_content(msg.get("content"))
            if text_content:
                role = msg.get("role", "unknown")
                role_label = (
                    "Uživatel"
                    if role == "user"
                    else "Asistent" if role == "assistant" else role
                )
                aggregated_parts.append(f"{text_content}")

        if not aggregated_parts:
            error_message = "Nelze získat platný obsah uživatelské zprávy."
            await self._emit_notification(__event_emitter__, error_message, "error")
            return {
                "messages": [{"role": "assistant", "content": f"❌ {error_message}"}]
            }

        original_content = "\n\n---\n\n".join(aggregated_parts)

        parts = re.split(r"```html.*?```", original_content, flags=re.DOTALL)
        long_text_content = ""
        if parts:
            for part in reversed(parts):
                if part.strip():
                    long_text_content = part.strip()
                    break

        if not long_text_content:
            long_text_content = original_content.strip()

        if len(long_text_content) < self.valves.MIN_TEXT_LENGTH:
            short_text_message = f"Textový obsah je příliš krátký ({len(long_text_content)} znaků), nelze provést efektivní analýzu. Prosím zadejte alespoň {self.valves.MIN_TEXT_LENGTH} znaků textu."
            await self._emit_notification(
                __event_emitter__, short_text_message, "warning"
            )
            return {
                "messages": [
                    {"role": "assistant", "content": f"⚠️ {short_text_message}"}
                ]
            }

        await self._emit_status(
            __event_emitter__,
            "Chytrá myšlenková mapa: Hloubková analýza struktury textu...",
            False,
        )

        try:
            unique_id = f"id_{int(time.time() * 1000)}"

            formatted_user_prompt = USER_PROMPT_GENERATE_MINDMAP.format(
                user_name=user_name,
                current_date_time_str=current_date_time_str,
                current_weekday=current_weekday_zh,
                current_timezone_str=current_timezone_str,
                user_language=user_language,
                long_text_content=long_text_content,
            )

            # Určení modelu k použití
            target_model = self.valves.MODEL_ID
            if not target_model:
                target_model = body.get("model")

            llm_payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_MINDMAP_ASSISTANT},
                    {"role": "user", "content": formatted_user_prompt},
                ],
                "temperature": 0.5,
                "stream": False,
            }
            user_obj = Users.get_user_by_id(user_id)
            if not user_obj:
                raise ValueError(f"Nelze získat objekt uživatele, user ID: {user_id}")

            llm_response = await generate_chat_completion(
                __request__, llm_payload, user_obj
            )

            if (
                not llm_response
                or "choices" not in llm_response
                or not llm_response["choices"]
            ):
                raise ValueError("Formát odpovědi LLM je nesprávný nebo prázdný.")

            assistant_response_content = llm_response["choices"][0]["message"][
                "content"
            ]
            markdown_syntax = self._extract_markdown_syntax(assistant_response_content)

            # Příprava komponent obsahu
            content_html = (
                CONTENT_TEMPLATE_MINDMAP.replace("{unique_id}", unique_id)
                .replace("{user_name}", user_name)
                .replace("{current_date_time_str}", current_date_time_str)
                .replace("{current_year}", current_year)
                .replace("{markdown_syntax}", markdown_syntax)
            )

            script_html = SCRIPT_TEMPLATE_MINDMAP.replace("{unique_id}", unique_id)

            # Extrakce existujícího HTML pokud existuje
            existing_html_block = ""
            match = re.search(
                r"```html\s*(<!-- OPENWEBUI_PLUGIN_OUTPUT -->[\s\S]*?)```",
                long_text_content,
            )
            if match:
                existing_html_block = match.group(1)

            if self.valves.CLEAR_PREVIOUS_HTML:
                long_text_content = self._remove_existing_html(long_text_content)
                final_html = self._merge_html(
                    "", content_html, CSS_TEMPLATE_MINDMAP, script_html, user_language
                )
            else:
                # Pokud jsme našli existující HTML, odstraníme starý blok z textu a sloučíme do něj
                if existing_html_block:
                    long_text_content = self._remove_existing_html(long_text_content)
                    final_html = self._merge_html(
                        existing_html_block,
                        content_html,
                        CSS_TEMPLATE_MINDMAP,
                        script_html,
                        user_language,
                    )
                else:
                    final_html = self._merge_html(
                        "",
                        content_html,
                        CSS_TEMPLATE_MINDMAP,
                        script_html,
                        user_language,
                    )

            # Kontrola režimu výstupu
            if self.valves.OUTPUT_MODE == "image":
                # Režim obrázku: použití JavaScriptu pro vykreslení a vložení jako Markdown obrázek
                chat_ctx = self._get_chat_context(body, __metadata__)
                chat_id = chat_ctx["chat_id"]
                message_id = chat_ctx["message_id"]

                await self._emit_status(
                    __event_emitter__,
                    "Chytrá myšlenková mapa: Vykresluji obrázek...",
                    False,
                )

                if __event_call__:
                    js_code = self._generate_image_js_code(
                        unique_id=unique_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        markdown_syntax=markdown_syntax,
                    )

                    await __event_call__(
                        {
                            "type": "execute",
                            "data": {"code": js_code},
                        }
                    )

                await self._emit_status(
                    __event_emitter__, "Chytrá myšlenková mapa: Obrázek vygenerován!", True
                )
                await self._emit_notification(
                    __event_emitter__,
                    f"Obrázek myšlenkové mapy byl vygenerován, {user_name}!",
                    "success",
                )
                logger.info("Action: Chytrá myšlenková mapa (v0.9.1) dokončena v režimu obrázku")
                return body

            # HTML režim (výchozí): vložení jako HTML blok
            html_embed_tag = f"```html\n{final_html}\n```"
            body["messages"][-1]["content"] = f"{long_text_content}\n\n{html_embed_tag}"

            await self._emit_status(
                __event_emitter__, "Chytrá myšlenková mapa: Kreslení dokončeno!", True
            )
            await self._emit_notification(
                __event_emitter__,
                f"Myšlenková mapa byla vygenerována, {user_name}!",
                "success",
            )
            logger.info("Action: Chytrá myšlenková mapa (v0.9.1) dokončena v HTML režimu")

        except Exception as e:
            error_message = f"Zpracování chytré myšlenkové mapy selhalo: {str(e)}"
            logger.error(f"Chyba chytré myšlenkové mapy: {error_message}", exc_info=True)
            user_facing_error = f"Omlouváme se, Chytrá myšlenková mapa narazila na chybu během zpracování: {str(e)}.\nProsím zkontrolujte backend logy Open WebUI pro více detailů."
            body["messages"][-1][
                "content"
            ] = f"{long_text_content}\n\n❌ **Chyba:** {user_facing_error}"

            await self._emit_status(
                __event_emitter__, "Chytrá myšlenková mapa: Zpracování selhalo.", True
            )
            await self._emit_notification(
                __event_emitter__,
                f"Generování chytré myšlenkové mapy selhalo, {user_name}!",
                "error",
            )

        return body
