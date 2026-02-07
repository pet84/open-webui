"""
title: 📊 Chytrá infografika (AntV)
author: Fu-Jie
author_url: https://github.com/Fu-Jie/awesome-openwebui
funding_url: https://github.com/open-webui
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPgogIDxsaW5lIHgxPSIxMiIgeTE9IjIwIiB4Mj0iMTIiIHkyPSIxMCIgLz4KICA8bGluZSB4MT0iMTgiIHkxPSIyMCIgeDI9IjE4IiB5Mj0iNCIgLz4KICA8bGluZSB4MT0iNiIgeTE9IjIwIiB4Mj0iNiIgeTI9IjE2IiAvPgo8L3N2Zz4=
version: 1.4.9
openwebui_id: ad6f0c7f-c571-4dea-821d-8e71697274cf
description: AI generátor infografik založený na AntV Infographic. Podporuje profesionální šablony, automatické párování ikon a stahování SVG/PNG.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Callable, Awaitable
import logging
import time
import re
from fastapi import Request
from datetime import datetime

from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import Users

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =================================================================
# LLM Prompty
# =================================================================

SYSTEM_PROMPT_INFOGRAPHIC_ASSISTANT = """
Jsi profesionální expert na návrh infografik. Umíš analyzovat text od uživatele a převést ho do formátu AntV Infographic.

## Specifikace syntaxe infografiky

Syntaxe infografiky je deklarativní zápis podobný Mermaid pro popis šablon, dat a témat.

### Pravidla syntaxe
- Záznam začíná `infographic <nazev-sablony>`
- Klíč–hodnota je oddělena mezerou, **žádné dvojtečky**
- Odsazení má 2 mezery
- Pole objektů používají `-` a zalomení řádků

⚠️ **DŮLEŽITÉ: Není to YAML!**
- ❌ Špatně: `children:` `items:` `data:` (s dvojtečkou)
- ✅ Správně: `children` `items` `data` (bez dvojtečky)

### Knihovna šablon a výběr

Vyber nejvhodnější šablonu podle struktury obsahu.

**Doporučení pro výběr šablony (oficiální):**
- Přísná posloupnost (procesy/kroky/trendy) → řada `sequence-*`
  - Časová osa → `sequence-timeline-simple`
  - Roadmapa → `sequence-roadmap-vertical-simple`
  - Cikcak kroky → `sequence-horizontal-zigzag-underline-text`
  - Hadí kroky → `sequence-snake-steps-compact-card`
  - 3D schody (KPI/růst/pokrok s hodnotami) → `sequence-ascending-stairs-3d-simple`
- Výčet pohledů → `list-row-horizontal-icon-arrow` nebo `list-column-simple-vertical-arrow`
- Srovnání (A vs B) → `compare-binary-horizontal-underline-text-vs`
- SWOT analýza → `compare-swot`
- Hierarchie (strom) → `hierarchy-tree-tech-style-capsule-item`
- Grafy → řada `chart-*`
- Kvadrantová analýza → `quadrant-quarter-simple-card`
- Mřížkový seznam (odrážky) → `list-grid-candy-card-lite`
- Zobrazení vztahů → `relation-circle-icon-badge`

**Dostupné šablony:**

*Sequence (时序/流程):*
`sequence-timeline-simple`, `sequence-roadmap-vertical-simple`, `sequence-horizontal-zigzag-underline-text`, 
`sequence-snake-steps-compact-card`, `sequence-zigzag-steps-underline-text`, `sequence-circular-simple`,
`sequence-pyramid-simple`, `sequence-ascending-steps`, `sequence-ascending-stairs-3d-simple`

*List (列表):*
`list-grid-candy-card-lite`, `list-grid-badge-card`, `list-row-horizontal-icon-arrow`,
`list-column-simple-vertical-arrow`, `list-column-done-list`

*Compare (对比):*
`compare-binary-horizontal-underline-text-vs`, `compare-binary-horizontal-simple-fold`,
`compare-hierarchy-left-right-circle-node-pill-badge`, `compare-swot`

*Hierarchy (层级):*
`hierarchy-tree-tech-style-capsule-item`, `hierarchy-tree-curved-line-rounded-rect-node`, `hierarchy-structure`

*Chart (图表):*
`chart-column-simple`, `chart-bar-plain-text`, `chart-line-plain-text`, 
`chart-pie-plain-text`, `chart-pie-donut-plain-text`, `chart-wordcloud`

*Other:*
`quadrant-quarter-simple-card`, `relation-circle-icon-badge`

**Textová kapacita podle typu šablony:**
- VYSOKÁ kapacita (dlouhý popis OK): `list-column-*`, `compare-binary-*`, `sequence-timeline-*`
- STŘEDNÍ kapacita: `list-row-*`, `sequence-roadmap-*`
- NÍZKÁ kapacita (krátké texty): `list-grid-*`, `hierarchy-*`, `sequence-steps`

### Ikony a ilustrace

**Ikony (Iconify):**
- Formát: `<kolekce>/<nazev-ikony>`, např. `mdi/rocket-launch`
- Oblíbené: `mdi/*` (Material Design), `fa/*` (Font Awesome), `bi/*` (Bootstrap)
- Příklady: `mdi/code-tags`, `mdi/chart-line`, `mdi/account-group`, `mdi/cloud`

**Ilustrace (unDraw):**
- Formát: název souboru bez .svg, např. `coding`, `team-work`
- Použij pole `illus` místo `icon`

### Příklady datové struktury

#### A. Standardní seznam/strom (výchozí)
Použij `items` a `children`.

```infographic
infographic list-grid
data
  title Moduly projektu
  items
    - label Modul A
      desc Popis modulu A
    - label Modul B
      desc Popis modulu B
```

#### B. Binární srovnání
Použij `items` pro dvě strany a `children` pro body srovnání.

```infographic
infographic compare-binary
data
  title Výhody vs Nevýhody
  desc Srovnání dvou aspektů
  items
    - label Výhody
      children
        - label Silné R&D
          desc Špičková inovace
        - label Věrnost zákazníků
          desc Návratnost přes 60 %
    - label Nevýhody
      children
        - label Slabý branding
          desc Nízké povědomí
        - label Úzké kanály
          desc Málo online kanálů
```

#### C. SWOT analýza
Použij `children` pro 4 kvadranty (Strengths, Weaknesses, Opportunities, Threats).

```infographic
infographic compare-swot
data
  title SWOT analýza produktu
  items
    - label Interní faktory
      children
        - label Silné stránky
          children
            - label Vysoký výkon
            - label Nízké náklady
        - label Slabé stránky
          children
            - label Omezené funkce
    - label Externí faktory
      children
        - label Příležitosti
          children
            - label Rostoucí trh
        - label Hrozby
          children
            - label Nová konkurence
```

#### D. Kvadrantový graf
Použij `items` pro kvadranty a `illus` pro ikony.

```infographic
infographic quadrant-quarter
data
  title Matice priorit
  items
    - label Vysoká důležitost
      children
        - label Urgentní
          desc Udělat hned
          illus mdi/alert
        - label Neurgentní
          desc Naplánovat
          illus mdi/calendar
    - label Nízká důležitost
      children
        - label Urgentní
          desc Delegovat
          illus mdi/account-arrow-right
        - label Neurgentní
          desc Zrušit
          illus mdi/delete
```

#### E. Stylizace
Vizuální styl nastavíš pomocí bloku `theme`.

**Podporované styly (`stylize`):**
- `rough`: ručně kreslený styl
- `pattern`: vzorovaná výplň
- `linear-gradient`: lineární přechod
- `radial-gradient`: radiální přechod

**Příklad (Rough):**
```infographic
infographic list-row-simple-horizontal-arrow
theme
  stylize rough
data
  ...
```

**Příklad (Gradient):**
```infographic
infographic chart-bar
theme
  stylize linear-gradient
data
  ...
```
#### F. Grafy (sloupcový/čárový/koláčový)
Použij `items` s `label` a `value`.

```infographic
infographic chart-bar
data
  title Tržby po kvartálech
  items
    - label Q1
      value 120
    - label Q2
      value 150
    - label Q3
      value 180
    - label Q4
      value 220
```

#### G. 3D Schody (KPI/růst/pokrok)
Použij `sequences` (ne `items`) s `label`, `value`, `time` a volitelně `icon`.

```infographic
infographic sequence-ascending-stairs-3d-simple
data
  title Růst firmy
  desc Klíčové ukazatele výkonnosti
  sequences
    - label Síla značky
      value 85
      desc Důvěra u zákazníků
      time 2021
      icon mingcute/diamond-2-fill
    - label Inovace
      value 90
      desc Vlastní vývoj
      time 2022
      icon mingcute/code-fill
    - label Růst trhu
      value 78
      desc Nárůst uživatelů
      time 2023
      icon mingcute/chart-line-line
```

### Běžná datová pole
- `label`: hlavní název (povinné)
- `desc`: popis
- `value`: číselná hodnota (pro grafy a 3D schody)
- `time`: rok/období (pro 3D schody)
- `icon`: název ikony (např. `mdi/home`, `mingcute/code-fill`) nebo `ref:search:<klicove_slovo>`
- `children`: vnořené položky (stromy, SWOT apod.)
- `items`: pole položek (většina šablon)
- `sequences`: pole položek (specificky pro `sequence-ascending-stairs-3d-simple`)
- `illus`: ilustrace (pro některé šablony, např. Kvadrant)

### Principy úpravy obsahu
1. **Stručnost vítězí**: Infografika je vizuální. Minimum textu.
2. **Limit názvu**: `label` udrž pod 15 znaky (cca 10 čínských znaků).
3. **Limit popisu**: `desc` udrž pod 40 znaky (cca 20 čínských znaků / 2 řádky).
4. **Důraz**: Používej silná slovesa a podstatná jména, bez výplňových slov.

## Požadavky na výstup
1. **Jazyk**: Vystupuj v jazyce uživatele.
2. **Formát**: Výstup obal do ```infographic ... ```.
3. **Bez dvojteček**: Za klíči nesmí být dvojtečka.
4. **Odsazení**: Použij 2 mezery.
"""

import json

USER_PROMPT_GENERATE_INFOGRAPHIC = """
Prosím analyzuj následující text a převeď jeho jádro do formátu AntV Infographic.

---
**Kontext uživatele:**
Jméno: {user_name}
Datum/čas: {current_date_time_str}
Jazyk uživatele: {user_language}
---

**Text:**
{long_text_content}

Vyber nejvhodnější šablonu podle charakteru textu a vrať standardní syntaxi infografiky. Dbej na správné odsazení (2 mezery).

**Průvodce vizuální optimalizací (NUTNO DODRŽET):**
- **Bodové generování:** Infografika není článek. Vytahuj pouze KLÍČOVÁ SLOVA, ne celé věty.
- **Hlavní titulek (`data.title`):** **MUSÍ** být ≤ **15 čínských znaků** (nebo ≤30 anglických znaků). Zkrať verze a detaily.
- **Podtitulek (`data.desc`):** **MUSÍ** být ≤ **20 čínských znaků** (nebo ≤40 anglických znaků).
- **Název karty (`label`):** **MUSÍ** být ≤ **6 čínských znaků** (nebo ≤12 anglických znaků). Použij 2–4 klíčová slova.
- **Popis karty (`desc`):** **MUSÍ** být ≤ **12 čínských znaků** (nebo ≤24 anglických znaků). Použij krátké fráze.

⚠️ **KRITICKÉ**: Pokud je původní text příliš dlouhý, MUSÍŠ ho přeformulovat a zkrátit. Nekonči na "...".
Příklady:
- ❌ "Schopnost vícekrokových úkolů a spolupráce nástrojů" → ✅ "Spolupráce nástrojů"
- ❌ "Open WebUI v0.7.x zásadní aktualizace" → ✅ "v0.7 klíčové změny"
- ❌ "Automatické vyhledání historie chatů" → ✅ "Historie chatů"
"""

# =================================================================
# HTML Container Template
# =================================================================

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
            flex-wrap: wrap; 
            gap: 20px; 
            align-items: flex-start; 
            width: 100%;
        }
        .plugin-item { 
            flex: 1 1 400px;
            min-width: 300px; 
            border-radius: 12px; 
            overflow: hidden; 
            transition: all 0.3s ease;
        }
        .plugin-item:hover {
            transform: translateY(-2px);
        }
        @media (max-width: 768px) { 
            .plugin-item { flex: 1 1 100%; } 
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

# =================================================================
# CSS Style Template
# =================================================================

CSS_TEMPLATE_INFOGRAPHIC = """
:root {
    --ig-primary-color: #6366f1;
    --ig-secondary-color: #8b5cf6;
    --ig-tertiary-color: #10b981;
    --ig-background-color: #f8fafc;
    --ig-card-bg-color: #ffffff;
    --ig-text-color: #1e293b;
    --ig-muted-text-color: #64748b;
    --ig-border-color: #e2e8f0;
    --ig-header-gradient: linear-gradient(135deg, #6366f1, #8b5cf6);
}
.infographic-container-wrapper {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    color: var(--ig-text-color);
    height: 100%;
    display: flex;
    flex-direction: column;
}
.infographic-container-wrapper .header {
    background: var(--ig-header-gradient);
    color: white;
    padding: 20px 24px;
    text-align: center;
}
.infographic-container-wrapper .header h1 {
    margin: 0;
    font-size: 1.5em;
    font-weight: 600;
}
.infographic-container-wrapper .user-context {
    font-size: 0.8em;
    color: var(--ig-muted-text-color);
    background-color: #f1f5f9;
    padding: 8px 16px;
    display: flex;
    justify-content: space-around;
    flex-wrap: wrap;
    border-bottom: 1px solid var(--ig-border-color);
}
.infographic-container-wrapper .content-area {
    padding: 20px;
    flex-grow: 1;
}
.infographic-container-wrapper .infographic-render-container {
    border-radius: 8px;
    padding: 16px;
    min-height: 600px;
    background: #fff;
    overflow: visible;
    transition: height 0.3s ease;
}
.infographic-render-container svg {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
}
.infographic-render-container svg * {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
}
.infographic-render-container svg text {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
}
.infographic-render-container svg foreignObject {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
    line-height: 1.3 !important;
    overflow: visible !important;
}
/* Main title styles */
.infographic-render-container svg foreignObject[data-element-type="title"] > * {
    font-size: 1.3em !important;
    font-weight: 800 !important;
    line-height: 1.3 !important;
    white-space: normal !important;
    word-break: break-word !important;
    display: -webkit-box !important;
    -webkit-line-clamp: 2 !important;
    -webkit-box-orient: vertical !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    text-align: center !important;
}
/* Page subtitle styles */
.infographic-render-container svg foreignObject[data-element-type="desc"] > * {
    font-size: 0.85em !important;
    line-height: 1.3 !important;
    white-space: normal !important;
    word-break: break-word !important;
    overflow: visible !important;
    text-align: center !important;
    display: block !important;
    color: var(--ig-muted-text-color) !important;
}
/* Card title styles */
.infographic-render-container svg foreignObject[data-element-type="item-label"] > * {
    font-size: 0.9em !important;
    font-weight: 600 !important;
    line-height: 1.3 !important;
    white-space: normal !important;
    word-break: break-word !important;
    display: -webkit-box !important;
    -webkit-line-clamp: 2 !important;
    -webkit-box-orient: vertical !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    padding-bottom: 2px !important;
}
/* Card description text */
.infographic-render-container svg foreignObject[data-element-type="item-desc"] > * {
    font-size: 0.8em !important;
    line-height: 1.4 !important;
    white-space: normal !important;
    word-break: break-word !important;
    display: -webkit-box !important;
    -webkit-line-clamp: 2 !important;
    -webkit-box-orient: vertical !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
.infographic-container-wrapper .download-area {
    text-align: center;
    padding-top: 20px;
    margin-top: 20px;
    border-top: 1px solid var(--ig-border-color);
}
.infographic-container-wrapper .download-btn {
    background-color: var(--ig-primary-color);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.9em;
    cursor: pointer;
    transition: all 0.2s;
    margin: 4px 6px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.infographic-container-wrapper .download-btn.secondary {
    background-color: var(--ig-secondary-color);
}
.infographic-container-wrapper .download-btn.tertiary {
    background-color: var(--ig-tertiary-color);
}
.infographic-container-wrapper .download-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.infographic-container-wrapper .footer {
    text-align: center;
    padding: 16px;
    font-size: 0.8em;
    color: var(--ig-muted-text-color);
    background-color: #f8fafc;
    border-top: 1px solid var(--ig-border-color);
}
.infographic-container-wrapper .error-message {
    color: #dc2626;
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    padding: 16px;
    border-radius: 8px;
    text-align: center;
}
"""

# =================================================================
# HTML Content Template
# =================================================================

CONTENT_TEMPLATE_INFOGRAPHIC = """
<div class="infographic-container-wrapper">
    <div class="header">
        <h1>📊 Chytrá infografika</h1>
    </div>
    <div class="user-context">
        <span><strong>Uživatel:</strong> {user_name}</span>
        <span><strong>Čas:</strong> {current_date_time_str}</span>
    </div>
    <div class="content-area">
        <div class="infographic-render-container" id="infographic-container-{unique_id}"></div>
        <div class="download-area">
            <button id="download-svg-btn-{unique_id}" class="download-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <span class="btn-text">Stáhnout SVG</span>
            </button>
            <button id="download-png-btn-{unique_id}" class="download-btn secondary">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                </svg>
                <span class="btn-text">Stáhnout PNG</span>
            </button>
            <button id="download-html-btn-{unique_id}" class="download-btn tertiary">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="16 18 22 12 16 6"/>
                    <polyline points="8 6 2 12 8 18"/>
                </svg>
                <span class="btn-text">Stáhnout HTML</span>
            </button>
        </div>
    </div>
    <div class="footer">
        <p>© {current_year} Infografika • <a href="https://infographic.antv.vision/" target="_blank" style="display: inline-flex; align-items: center; vertical-align: middle;">
            <svg width="24" height="25" viewBox="0 0 291 300" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-left: 4px;">
                <g><path d="M140.904 239.376C128.83 239.683 119.675 239.299 115.448 243.843C110.902 248.07 111.288 257.227 110.979 269.302C111.118 274.675 111.118 279.478 111.472 283.52C111.662 285.638 111.95 287.547 112.406 289.224C112.411 289.243 112.416 289.259 112.422 289.28C112.462 289.419 112.496 289.558 112.539 289.691C113.168 291.787 114.088 293.491 115.446 294.758C116.662 296.064 118.283 296.963 120.264 297.59C120.36 297.614 120.464 297.646 120.555 297.675C120.56 297.68 120.56 297.68 120.566 297.68C120.848 297.768 121.142 297.846 121.443 297.923C121.454 297.923 121.464 297.928 121.478 297.934C122.875 298.272 124.424 298.507 126.11 298.678C126.326 298.696 126.542 298.718 126.763 298.739C130.79 299.086 135.558 299.088 140.904 299.222C152.974 298.912 162.128 299.302 166.36 294.758C170.904 290.526 170.515 281.371 170.824 269.302C170.515 257.227 170.907 248.07 166.36 243.843C162.131 239.299 152.974 239.683 140.904 239.376Z" fill="#FF6376"></path><path d="M21.2155 128.398C12.6555 128.616 6.16484 128.339 3.16751 131.56C-0.0538222 134.56 0.218178 141.054 -0.000488281 149.608C0.218178 158.168 -0.0538222 164.659 3.16751 167.656C6.16484 170.878 12.6555 170.606 21.2155 170.824C25.0262 170.726 28.4288 170.726 31.2955 170.475C32.7968 170.342 34.1488 170.136 35.3382 169.814C35.3542 169.811 35.3648 169.806 35.3782 169.803C35.4768 169.774 35.5755 169.747 35.6688 169.718C37.1568 169.272 38.3648 168.622 39.2635 167.656C40.1915 166.795 40.8262 165.646 41.2715 164.243C41.2875 164.174 41.3115 164.102 41.3328 164.035C41.3328 164.035 41.3355 164.032 41.3355 164.027C41.3968 163.827 41.4529 163.622 41.5062 163.406C41.5062 163.398 41.5115 163.392 41.5142 163.382C41.7542 162.392 41.9222 161.294 42.0422 160.096C42.0555 159.944 42.0715 159.792 42.0848 159.635C42.3328 156.779 42.3328 153.398 42.4262 149.608C42.2075 141.054 42.4848 134.56 39.2635 131.56C36.2635 128.339 29.7728 128.616 21.2155 128.398Z" fill="#FFCCCC"></path><path d="M81.0595 184.171C70.8568 184.433 63.1208 184.102 59.5475 187.942C55.7075 191.518 56.0328 199.254 55.7742 209.454C56.0328 219.657 55.7075 227.393 59.5475 230.963C63.1208 234.803 70.8568 234.478 81.0595 234.739C85.6008 234.622 89.6595 234.622 93.0728 234.323C94.8648 234.163 96.4755 233.921 97.8942 233.534C97.9102 233.529 97.9235 233.526 97.9422 233.521C98.0568 233.486 98.1742 233.457 98.2888 233.422C100.06 232.889 101.5 232.113 102.569 230.963C103.676 229.937 104.433 228.566 104.964 226.894C104.985 226.811 105.012 226.726 105.036 226.646C105.041 226.643 105.041 226.643 105.041 226.638C105.116 226.401 105.18 226.153 105.244 225.897C105.244 225.889 105.249 225.881 105.254 225.867C105.54 224.689 105.74 223.379 105.881 221.953C105.9 221.771 105.916 221.59 105.934 221.403C106.228 218.001 106.228 213.969 106.342 209.454C106.081 199.254 106.412 191.518 102.572 187.942C98.9955 184.102 91.2568 184.433 81.0595 184.171Z" fill="#FF939F"></path><path d="M260.591 151.87C215.652 151.87 203.02 164.523 203.02 209.462H198.476C198.476 164.523 185.836 151.881 140.895 151.881V147.337C185.836 147.337 198.487 134.705 198.487 89.7659H203.02C203.02 134.705 215.652 147.337 260.591 147.337V151.87ZM286.052 124.158C281.82 119.614 272.66 120.001 260.591 119.689C248.521 119.385 239.361 119.771 235.129 115.227C230.585 110.995 230.983 101.846 230.671 89.7659C230.513 83.7312 230.535 78.4272 230.023 74.1019C229.513 69.7659 228.481 66.4219 226.209 64.3046C221.967 59.7606 212.817 60.1472 200.748 59.8459C188.681 60.1472 179.519 59.7606 175.287 64.3046C170.753 68.5366 171.129 77.6966 170.828 89.7659C170.516 101.835 170.9 110.995 166.356 115.227C162.124 119.771 152.985 119.374 140.905 119.689C138.873 119.739 136.924 119.771 135.071 119.811C119.313 118.697 106.337 112.318 106.337 89.7659C106.212 84.6699 106.233 80.1792 105.807 76.5206C105.367 72.8726 104.492 70.0379 102.575 68.2566C99.0013 64.4112 91.2573 64.7446 81.0653 64.4832C70.86 64.7446 63.1186 64.4112 59.5533 68.2566C55.708 71.8299 56.0306 79.5632 55.7693 89.7659C56.0306 99.9686 55.708 107.702 59.5533 111.278C63.1186 115.113 70.86 114.79 81.0653 115.049C103.617 115.049 109.996 128.035 111.1 143.803C111.068 145.659 111.028 147.587 110.975 149.619C111.121 154.987 111.121 159.79 111.476 163.835C111.663 165.95 111.945 167.857 112.404 169.534C112.412 169.555 112.412 169.566 112.423 169.598C112.465 169.734 112.497 169.867 112.537 170.003C113.164 172.099 114.092 173.809 115.447 175.07C116.665 176.371 118.281 177.278 120.271 177.905C120.364 177.934 120.46 177.955 120.564 177.987C120.855 178.081 121.145 178.153 121.439 178.238C121.46 178.238 121.471 178.238 121.479 178.249C122.876 178.582 124.42 178.822 126.108 178.987C126.327 179.009 126.545 179.03 126.764 179.051C130.788 179.395 135.559 179.395 140.905 179.529C152.975 179.843 162.124 179.457 166.356 184.001C170.9 188.233 170.516 197.371 170.828 209.451C171.129 221.529 170.743 230.681 175.287 234.91C179.519 239.454 188.681 239.07 200.748 239.371C206.127 239.235 210.921 239.235 214.975 238.881C217.079 238.694 218.985 238.403 220.676 237.955C220.695 237.945 220.705 237.934 220.727 237.934C220.873 237.891 220.999 237.859 221.135 237.819C223.228 237.193 224.937 236.265 226.209 234.91C227.511 233.691 228.409 232.065 229.044 230.097C229.065 230.003 229.095 229.899 229.127 229.803V229.793C229.22 229.513 229.295 229.222 229.367 228.918C229.367 228.897 229.377 228.897 229.377 228.878C229.721 227.481 229.951 225.937 230.127 224.249C230.137 224.03 230.169 223.811 230.191 223.593C230.535 219.571 230.535 214.798 230.671 209.451C230.972 197.371 230.585 188.233 235.129 184.001C239.361 179.457 248.511 179.843 260.591 179.529C272.66 179.227 281.82 179.614 286.052 175.07C290.596 170.838 290.209 161.689 290.511 149.619C290.209 137.539 290.596 128.379 286.052 124.158Z" fill="#FF356A"></path><path d="M112.405 49.848C112.411 49.8694 112.416 49.8827 112.421 49.904C112.461 50.0427 112.499 50.1814 112.539 50.3147C113.171 52.4134 114.088 54.1147 115.448 55.384C116.661 56.6907 118.283 57.5894 120.264 58.2134C120.36 58.24 120.464 58.2694 120.555 58.3014C120.56 58.3067 120.56 58.3067 120.565 58.3067C120.848 58.3947 121.141 58.4694 121.443 58.5467C121.453 58.5467 121.464 58.552 121.48 58.5574C122.875 58.896 124.424 59.1334 126.112 59.3014C126.325 59.3227 126.541 59.3414 126.763 59.3627C130.789 59.712 135.56 59.712 140.904 59.8454C152.973 59.5387 162.128 59.928 166.36 55.384C170.907 51.152 170.515 41.9947 170.824 29.9254C170.517 17.8507 170.907 8.69602 166.363 4.46935C162.131 -0.0746511 152.973 0.309349 140.904 1.52588e-05C128.829 0.309349 119.675 -0.0746511 115.448 4.46935C110.904 8.69602 111.288 17.8507 110.979 29.9254C111.117 35.3014 111.117 40.1014 111.472 44.144C111.661 46.2614 111.949 48.1707 112.405 49.848Z" fill="#FF6376"></path></g>
            </svg>
        </a></p>
    </div>
</div>

<script type="text/template" id="infographic-source-{unique_id}">{infographic_syntax}</script>
"""

# =================================================================
# JavaScript Rendering Script
# =================================================================

SCRIPT_TEMPLATE_INFOGRAPHIC = """
<script src="https://unpkg.com/@antv/infographic@latest/dist/infographic.min.js"></script>
<script>
(function() {{
    const renderInfographic = () => {{
        const uniqueId = "{unique_id}";
        const containerEl = document.getElementById('infographic-container-' + uniqueId);
        if (!containerEl || containerEl.dataset.infographicRendered) return;

        const sourceEl = document.getElementById('infographic-source-' + uniqueId);
        if (!sourceEl) return;

        let syntaxContent = sourceEl.textContent.trim();
        if (!syntaxContent) {{
            containerEl.innerHTML = '<div class="error-message">⚠️ Nelze načíst infografiku: chybí platný obsah.</div>';
            return;
        }}

        console.log('[Infographic] Original syntax content:', syntaxContent);

        // Remove code block markers - use more robust string handling
        const backtick = String.fromCharCode(96);
        const prefix = backtick + backtick + backtick + 'infographic';
        const simplePrefix = backtick + backtick + backtick;
        
        if (syntaxContent.toLowerCase().startsWith(prefix)) {{
            syntaxContent = syntaxContent.substring(prefix.length).trim();
        }} else if (syntaxContent.startsWith(simplePrefix)) {{
            syntaxContent = syntaxContent.substring(simplePrefix.length).trim();
        }}
        
        if (syntaxContent.endsWith(simplePrefix)) {{
            syntaxContent = syntaxContent.substring(0, syntaxContent.length - simplePrefix.length).trim();
        }}

        // Fix syntax: remove colons after keywords (LLM may incorrectly add them)
        // e.g.: children: -> children, items: -> items, data: -> data
        syntaxContent = syntaxContent.replace(/^(data|items|children|theme|config):/gm, '$1');
        syntaxContent = syntaxContent.replace(/(\\s)(children|items):/g, '$1$2');

        // 1. Fallback check: ensure infographic prefix
        if (!syntaxContent.trim().toLowerCase().startsWith('infographic')) {{
            const firstWord = syntaxContent.trim().split(/\\s+/)[0].toLowerCase();
            if (!['data', 'theme', 'design', 'items'].includes(firstWord)) {{
                console.log('[Infographic] Missing prefix detected, auto-completing');
                syntaxContent = 'infographic ' + syntaxContent;
            }}
        }}

        // 2. Template Mapping Configuration (Official AntV Structure IDs)
        const TEMPLATE_MAPPING = {{
            // List & Hierarchy - map short names to full template names
            'list-grid': 'list-grid-compact-card',
            'list-column': 'list-column-simple-vertical-arrow',
            'list-row': 'list-row-simple-horizontal-arrow',
            'hierarchy-tree': 'hierarchy-tree-tech-style-capsule-item',
            
            // Sequence & Timeline
            'sequence-roadmap-vertical': 'sequence-roadmap-vertical-simple',
            'sequence-timeline': 'sequence-timeline-simple',
            'sequence-steps': 'sequence-steps-simple',
            'sequence-horizontal-zigzag': 'sequence-horizontal-zigzag-simple',
            
            // Comparison
            'compare-binary-horizontal': 'compare-binary-horizontal-simple-vs',
            'compare-hierarchy-row': 'compare-hierarchy-row-simple',
            
            // Charts
            'chart-column': 'chart-column-simple',
            'quadrant': 'quadrant-quarter-simple-card',
            
            // Legacy mappings for backward compatibility
            'list-vertical': 'list-column-simple-vertical-arrow',
            'tree-vertical': 'hierarchy-tree-tech-style-capsule-item',
            'sequence-roadmap': 'sequence-roadmap-vertical-simple',
            'sequence-zigzag': 'sequence-horizontal-zigzag-simple',
            'compare-binary': 'compare-binary-horizontal-simple-vs',
            'chart-bar': 'chart-bar-plain-text',
            'chart-line': 'chart-line-plain-text',
            'chart-pie': 'chart-pie-plain-text',
            'chart-doughnut': 'chart-pie-donut-plain-text'
        }};


        // 3. Apply Mapping Strategy
        for (const [key, value] of Object.entries(TEMPLATE_MAPPING)) {{
            const regex = new RegExp(`infographic\\\\s+${{key}}(?=\\\\s|$)`, 'i');
            if (regex.test(syntaxContent)) {{
                console.log(`[Infographic] Auto-mapping template: ${{key}} -> ${{value}}`);
                syntaxContent = syntaxContent.replace(regex, `infographic ${{value}}`);
                break; 
            }}
        }}

        // --- Style Extraction & Application ---
        const bgMatch = syntaxContent.match(/backgroundColor\\s+(#[0-9a-fA-F]{{6}}|#[0-9a-fA-F]{{3}}|[a-zA-Z]+)/);
        if (bgMatch && bgMatch[1]) {{
            containerEl.style.backgroundColor = bgMatch[1];
        }} else {{
            containerEl.style.backgroundColor = '#ffffff';
        }}

        const textMatch = syntaxContent.match(/textColor\\s+(#[0-9a-fA-F]{{6}}|#[0-9a-fA-F]{{3}}|[a-zA-Z]+)/);
        if (textMatch && textMatch[1]) {{
            containerEl.style.color = textMatch[1];
        }} else {{
             containerEl.style.color = '';
        }}

        // --- Syntax Cleaning ---
        // Remove unsupported theme properties
        const nl = String.fromCharCode(10);
        const cleanRegex = new RegExp('^\\\\s*(roughness|stylize|backgroundColor|textColor|colorBg).*(' + nl + '\\\\s+.*)*', 'gm');
        syntaxContent = syntaxContent.replace(cleanRegex, '');
        
        syntaxContent = syntaxContent.trim();
        
        // Temporary fallback strategy
        if (/infographic\\s+list-vertical/.test(syntaxContent)) {{
             console.log('[Infographic] Detected list-vertical, temporarily downgrading to list-row-simple-horizontal-arrow');
             syntaxContent = syntaxContent.replace(/infographic\\s+list-vertical/, 'infographic list-row-simple-horizontal-arrow');
        }}

        console.log('[Infographic] Cleaned syntax content:', syntaxContent);

        if (typeof AntVInfographic === 'undefined') {{
            console.error('[Infographic] AntVInfographic library not loaded');
            containerEl.innerHTML = '<div class="error-message">⚠️ Nelze načíst knihovnu AntV Infographic. Zkontrolujte připojení k síti.</div>';
            return;
        }}

        try {{
            const {{ Infographic }} = AntVInfographic;
            
            // Use ID selector string
            const containerId = '#' + containerEl.id;
            
            const instance = new Infographic({{
                container: containerId,
                width: '100%',
                // height: '100%', // Remove fixed height to allow auto-sizing
                padding: 24,
            }});
            
            console.log('[Infographic] Rendering...');
            instance.render(syntaxContent);
            containerEl.dataset.infographicRendered = 'true';
            console.log('[Infographic] Rendering complete');

            // Auto-adjust height and tag elements
            setTimeout(() => {
                const svg = containerEl.querySelector('svg');
                if (svg) {
                    // Force sans-serif inside SVG (AntV can inject its own font)
                    const sansFont = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif';
                    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
                    style.textContent = `
                      text, tspan, foreignObject, foreignObject * {
                        font-family: ${sansFont} !important;
                      }
                    `;
                    svg.prepend(style);
                    
                    // Force font directly on all text elements (overrides inline styles)
                    svg.querySelectorAll('text, tspan').forEach(el => {
                        el.setAttribute('font-family', sansFont);
                        el.style.fontFamily = sansFont;
                    });
                    svg.querySelectorAll('foreignObject *').forEach(el => {
                        el.style.fontFamily = sansFont;
                    });

                    // 1. Tag elements for CSS styling
                    const fos = Array.from(svg.querySelectorAll('foreignObject'));
                    let titleFound = false;
                    let descFound = false;
                    
                    fos.forEach((fo) => {
                        const text = fo.textContent.trim();
                        if (!text || fo.querySelector('i') || (fo.querySelector('svg') && fo.querySelectorAll('*').length < 5)) {
                            fo.setAttribute('data-element-type', 'icon');
                            return;
                        }
                        
                        // Dynamically increase height and width to accommodate wrapped text
                        const currentHeight = parseInt(fo.getAttribute('height') || '0');
                        if (currentHeight > 0 && currentHeight < 200) {
                            fo.setAttribute('height', Math.round(currentHeight * 1.8).toString());
                        }
                        const currentWidth = parseInt(fo.getAttribute('width') || '0');
                        if (currentWidth > 0 && currentWidth < 300) {
                            fo.setAttribute('width', Math.max(Math.round(currentWidth * 1.2), 180).toString());
                        }

                        if (!titleFound) {
                            fo.setAttribute('data-element-type', 'title');
                            titleFound = true;
                        } else if (!descFound) {
                            fo.setAttribute('data-element-type', 'desc');
                            descFound = true;
                        } else {
                            if (fo.querySelector('strong') || fo.style.fontWeight === 'bold' || text.length < 15) {
                                fo.setAttribute('data-element-type', 'item-label');
                            } else {
                                fo.setAttribute('data-element-type', 'item-desc');
                            }
                        }
                    });

                    // 2. Adjust height
                    const bbox = svg.getBoundingClientRect();
                    let contentHeight = bbox.height;
                    if (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.height) {
                        contentHeight = svg.viewBox.baseVal.height;
                    }
                    const finalHeight = contentHeight + 40; 
                    containerEl.style.minHeight = finalHeight + 'px';
                    containerEl.style.height = 'auto';
                }
            }, 500);
            
            attachDownloadHandlers(uniqueId, syntaxContent);

        }} catch (error) {{
            console.error('[Infographic] Rendering error:', error);
            containerEl.innerHTML = '<div class="error-message">⚠️ Vykreslení infografiky selhalo!<br>Důvod: ' + error.message + '</div>';
        }}
    }};

    const attachDownloadHandlers = (uniqueId, syntaxContent) => {{
        const downloadSvgBtn = document.getElementById('download-svg-btn-' + uniqueId);
        const downloadPngBtn = document.getElementById('download-png-btn-' + uniqueId);
        const downloadHtmlBtn = document.getElementById('download-html-btn-' + uniqueId);
        const containerEl = document.getElementById('infographic-container-' + uniqueId);

        const showFeedback = (button, isSuccess, msg) => {{
            const buttonText = button.querySelector('.btn-text');
            const originalText = buttonText.textContent;
            button.disabled = true;
            buttonText.textContent = isSuccess ? '✅ ' + (msg || 'Hotovo') : '❌ Selhalo';
            setTimeout(() => {{
                buttonText.textContent = originalText;
                button.disabled = false;
            }}, 2000);
        }};

        const downloadFile = (content, filename, mimeType) => {{
            const blob = new Blob([content], {{ type: mimeType }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }};

        if (downloadSvgBtn) {{
            downloadSvgBtn.addEventListener('click', (event) => {{
                event.stopPropagation();
                const svgEl = containerEl.querySelector('svg');
                if (svgEl) {{
                    const svgData = new XMLSerializer().serializeToString(svgEl);
                    downloadFile(svgData, 'infografika_' + uniqueId + '.svg', 'image/svg+xml');
                    showFeedback(downloadSvgBtn, true, 'Staženo');
                }} else {{
                    showFeedback(downloadSvgBtn, false);
                }}
            }});
        }}

        if (downloadPngBtn) {{
            downloadPngBtn.addEventListener('click', (event) => {{
                event.stopPropagation();
                const svgEl = containerEl.querySelector('svg');
                if (svgEl) {{
                    // Get SVG actual dimensions
                    const bbox = svgEl.getBoundingClientRect();
                    const width = bbox.width || svgEl.viewBox?.baseVal?.width || 800;
                    const height = bbox.height || svgEl.viewBox?.baseVal?.height || 600;
                    
                    // Clone SVG and set explicit dimensions
                    const clonedSvg = svgEl.cloneNode(true);
                    clonedSvg.setAttribute('width', width);
                    clonedSvg.setAttribute('height', height);
                    clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                    
                    const svgData = new XMLSerializer().serializeToString(clonedSvg);
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    const img = new Image();
                    
                    // Use Base64 encoding to avoid special character issues
                    const base64Data = btoa(unescape(encodeURIComponent(svgData)));
                    const dataUrl = 'data:image/svg+xml;base64,' + base64Data;
                    
                    img.onload = () => {{
                        const scale = 2;
                        canvas.width = width * scale;
                        canvas.height = height * scale;
                        ctx.scale(scale, scale);
                        ctx.fillStyle = '#ffffff';
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        ctx.drawImage(img, 0, 0, width, height);
                        
                        canvas.toBlob((blob) => {{
                            if (blob) {{
                                const pngUrl = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = pngUrl;
                                a.download = 'infografika_' + uniqueId + '.png';
                                a.click();
                                URL.revokeObjectURL(pngUrl);
                                showFeedback(downloadPngBtn, true, 'Staženo');
                            }} else {{
                                console.error('[Infographic] PNG blob creation failed');
                                showFeedback(downloadPngBtn, false);
                            }}
                        }}, 'image/png');
                    }};
                    
                    img.onerror = (err) => {{
                        console.error('[Infographic] SVG to image conversion failed:', err);
                        showFeedback(downloadPngBtn, false);
                    }};
                    
                    img.src = dataUrl;
                }} else {{
                    showFeedback(downloadPngBtn, false);
                }}
            }});
        }}

        if (downloadHtmlBtn) {{
            downloadHtmlBtn.addEventListener('click', (event) => {{
                event.stopPropagation();
                const htmlContent = `<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Infografika</title>
    <script src="https://unpkg.com/@antv/infographic@latest/dist/infographic.min.js"><\\/script>
    <style>
        body {{ margin: 0; padding: 20px; background: #f5f5f5; }}
        #container {{ background: white; border-radius: 8px; padding: 20px; max-width: 900px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div id="container"></div>
    <script>
        const {{ Infographic }} = AntVInfographic;
        const instance = new Infographic({{
            container: '#container',
            width: '100%',
            padding: 24,
        }});
        instance.render(\`${{syntaxContent.replace(/`/g, '\\\\`')}}\`);
    <\\/script>
</body>
</html>`;
                downloadFile(htmlContent, 'infografika_' + uniqueId + '.html', 'text/html');
                showFeedback(downloadHtmlBtn, true, 'Staženo');
            }});
        }}
    }};

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', renderInfographic);
    }} else {{
        renderInfographic();
    }}
}})();
</script>
"""


class Action:
    class Valves(BaseModel):
        SHOW_STATUS: bool = Field(
            default=True, description="Zobrazit průběh operace v chatu."
        )
        MODEL_ID: str = Field(
            default="",
            description="ID interního LLM modelu. Pokud je prázdné, použije se aktuální model.",
        )
        MIN_TEXT_LENGTH: int = Field(
            default=100,
            description="Minimální délka textu (v počtu znaků) pro analýzu infografiky.",
        )
        CLEAR_PREVIOUS_HTML: bool = Field(
            default=False,
            description="Vynutit smazání předchozího HTML (pokud True, přepisuje místo slučování).",
        )
        MESSAGE_COUNT: int = Field(
            default=1,
            description="Počet posledních zpráv pro generování. 1 = jen poslední zpráva.",
        )
        OUTPUT_MODE: str = Field(
            default="image",
            description="Režim výstupu: 'html' pro interaktivní HTML, nebo 'image' pro vložení jako obrázku (výchozí).",
        )
        SHOW_DEBUG_LOG: bool = Field(
            default=False,
            description="Zda tisknout debug logy do konzole prohlížeče.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def _get_user_context(self, __user__: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Bezpečně získá kontext uživatele."""
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
        Upřednostní data z body, poté z metadata.
        """
        chat_id = ""
        message_id = ""

        # 1. Zkus z body
        if isinstance(body, dict):
            chat_id = body.get("chat_id", "")
            message_id = body.get("id", "")

            # Fallback na body.metadata
            if not chat_id or not message_id:
                body_metadata = body.get("metadata", {})
                if isinstance(body_metadata, dict):
                    if not chat_id:
                        chat_id = body_metadata.get("chat_id", "")
                    if not message_id:
                        message_id = body_metadata.get("message_id", "")

        # 2. Zkus z __metadata__
        if __metadata__ and isinstance(__metadata__, dict):
            if not chat_id:
                chat_id = __metadata__.get("chat_id", "")
            if not message_id:
                message_id = __metadata__.get("message_id", "")

        return {
            "chat_id": str(chat_id).strip(),
            "message_id": str(message_id).strip(),
        }

    def _extract_infographic_syntax(self, llm_output: str) -> str:
        """Extrahuje syntaxi infografiky z výstupu LLM."""
        match = re.search(r"```infographic\s*(.*?)\s*```", llm_output, re.DOTALL)
        if match:
            extracted_content = match.group(1).strip()
        else:
            logger.warning(
                "Výstup LLM neměl očekávaný formát, bere se celý výstup jako syntaxe."
            )
            extracted_content = llm_output.strip()

        return extracted_content.replace("</script>", "<\\/script>")

    async def _emit_status(self, emitter, description: str, done: bool = False):
        """Pošle status událost"""
        if self.valves.SHOW_STATUS and emitter:
            await emitter(
                {"type": "status", "data": {"description": description, "done": done}}
            )

    async def _emit_notification(self, emitter, content: str, ntype: str = "info"):
        """Pošle notifikaci (info/success/warning/error)"""
        if emitter:
            await emitter(
                {"type": "notification", "data": {"type": ntype, "content": content}}
            )

    async def _emit_debug_log(self, emitter, title: str, data: dict):
        """Vypíše strukturované debug logy do konzole"""
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
            print(f"Chyba při odeslání debug logu: {e}")

    def _remove_existing_html(self, content: str) -> str:
        """Odstraní existující HTML bloky generované pluginem."""
        pattern = r"```html\s*<!-- OPENWEBUI_PLUGIN_OUTPUT -->[\s\S]*?```"
        return re.sub(pattern, "", content).strip()

    def _extract_text_content(self, content) -> str:
        """Vytáhne text z obsahu zprávy, včetně multimodálních formátů."""
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
        existing_html_code: str,
        new_content: str,
        new_styles: str = "",
        new_scripts: str = "",
        user_language: str = "cs",
    ) -> str:
        """Sloučí nový obsah do existujícího HTML nebo vytvoří nový."""
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
        infographic_syntax: str,
    ) -> str:
        """Vygeneruje JS kód pro vykreslení SVG a vložení obrázku."""

        # Escape the syntax for JS embedding
        syntax_escaped = (
            infographic_syntax.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
            .replace("</script>", "<\\/script>")
        )

        return f"""
(async function() {{
    const uniqueId = "{unique_id}";
    const chatId = "{chat_id}";
    const messageId = "{message_id}";
    const defaultWidth = 1100;
    const defaultHeight = 500;
    
    // Auto-detect chat container width for responsive sizing
    let svgWidth = defaultWidth;
    let svgHeight = defaultHeight;
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {{
        const containerWidth = chatContainer.clientWidth;
        if (containerWidth > 100) {{
            // Use container width with padding (80% of container, leaving more space on the right)
            svgWidth = Math.floor(containerWidth * 0.8);
            // Maintain aspect ratio based on default dimensions
            svgHeight = Math.floor(svgWidth * (defaultHeight / defaultWidth));
            console.log("[Infographic Image] Auto-detected container width:", containerWidth, "-> SVG:", svgWidth, "x", svgHeight);
        }}
    }}
    
    console.log("[Infographic Image] Starting render...");
    console.log("[Infographic Image] chatId:", chatId, "messageId:", messageId);
    
    try {{
        // Load AntV Infographic if not loaded
        if (typeof AntVInfographic === 'undefined') {{
            console.log("[Infographic Image] Loading AntV Infographic...");
            await new Promise((resolve, reject) => {{
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/@antv/infographic@latest/dist/infographic.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            }});
        }}
        
        const {{ Infographic }} = AntVInfographic;
        
        // Get syntax content
        let syntaxContent = `{syntax_escaped}`;
        console.log("[Infographic Image] Syntax length:", syntaxContent.length);
        
        // Clean up syntax: remove code block markers
        const backtick = String.fromCharCode(96);
        const prefix = backtick + backtick + backtick + 'infographic';
        const simplePrefix = backtick + backtick + backtick;
        
        if (syntaxContent.toLowerCase().startsWith(prefix)) {{
            syntaxContent = syntaxContent.substring(prefix.length).trim();
        }} else if (syntaxContent.startsWith(simplePrefix)) {{
            syntaxContent = syntaxContent.substring(simplePrefix.length).trim();
        }}
        
        if (syntaxContent.endsWith(simplePrefix)) {{
            syntaxContent = syntaxContent.substring(0, syntaxContent.length - simplePrefix.length).trim();
        }}
        
        // Fix syntax: remove colons after keywords
        syntaxContent = syntaxContent.replace(/^(data|items|children|theme|config):/gm, '$1');
        syntaxContent = syntaxContent.replace(/(\\s)(children|items):/g, '$1$2');
        
        // Ensure infographic prefix
        if (!syntaxContent.trim().toLowerCase().startsWith('infographic')) {{
            const firstWord = syntaxContent.trim().split(/\\s+/)[0].toLowerCase();
            if (!['data', 'theme', 'design', 'items'].includes(firstWord)) {{
                syntaxContent = 'infographic ' + syntaxContent;
            }}
        }}
        
        // Template mapping
        const TEMPLATE_MAPPING = {{
            'list-grid': 'list-grid-compact-card',
            'list-vertical': 'list-column-simple-vertical-arrow',
            'tree-vertical': 'hierarchy-tree-tech-style-capsule-item',
            'tree-horizontal': 'hierarchy-tree-lr-tech-style-capsule-item',
            'mindmap': 'hierarchy-mindmap-branch-gradient-capsule-item',
            'sequence-roadmap': 'sequence-roadmap-vertical-simple',
            'sequence-zigzag': 'sequence-horizontal-zigzag-simple',
            'sequence-horizontal': 'sequence-horizontal-zigzag-simple',
            'relation-sankey': 'relation-sankey-simple',
            'relation-circle': 'relation-circle-icon-badge',
            'compare-binary': 'compare-binary-horizontal-simple-vs',
            'compare-swot': 'compare-swot',
            'quadrant-quarter': 'quadrant-quarter-simple-card',
            'statistic-card': 'list-grid-compact-card',
            'chart-bar': 'chart-bar-plain-text',
            'chart-column': 'chart-column-simple',
            'chart-line': 'chart-line-plain-text',
            'chart-area': 'chart-area-simple',
            'chart-pie': 'chart-pie-plain-text',
            'chart-doughnut': 'chart-pie-donut-plain-text'
        }};
        
        for (const [key, value] of Object.entries(TEMPLATE_MAPPING)) {{
            const regex = new RegExp(`infographic\\\\s+${{key}}(?=\\\\s|$)`, 'i');
            if (regex.test(syntaxContent)) {{
                syntaxContent = syntaxContent.replace(regex, `infographic ${{value}}`);
                break;
            }}
        }}
        
        // Create offscreen container
        const container = document.createElement('div');
        container.id = 'infographic-offscreen-' + uniqueId;
        container.style.cssText = 'position:absolute;left:-9999px;top:-9999px;width:' + svgWidth + 'px;height:' + svgHeight + 'px;background:#ffffff;';
        document.body.appendChild(container);
        
        // Create infographic instance
        const instance = new Infographic({{
            container: '#' + container.id,
            width: svgWidth,
            height: svgHeight,
            padding: 12,
        }});
        
        console.log("[Infographic Image] Rendering infographic...");
        instance.render(syntaxContent);
        
        // Wait for render to complete
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Get SVG element
        const svgEl = container.querySelector('svg');
        if (!svgEl) {{
            throw new Error('SVG element not found after rendering');
        }}
        
        // Force sans-serif font on all text elements before export
        const sansFont = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif';
        svgEl.querySelectorAll('text, tspan').forEach(el => {{
            el.setAttribute('font-family', sansFont);
            el.style.fontFamily = sansFont;
        }});
        svgEl.querySelectorAll('foreignObject *').forEach(el => {{
            el.style.fontFamily = sansFont;
        }});
        
        // Get actual dimensions
        const bbox = svgEl.getBoundingClientRect();
        const width = bbox.width || svgWidth;
        const height = bbox.height || svgHeight;
        
        // Clone and prepare SVG for export
        const clonedSvg = svgEl.cloneNode(true);
        clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        clonedSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
        clonedSvg.setAttribute('width', width);
        clonedSvg.setAttribute('height', height);
        
        // Add font style to exported SVG
        const styleEl = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        styleEl.textContent = 'text, tspan, foreignObject, foreignObject * {{ font-family: ' + sansFont + ' !important; }}';
        clonedSvg.prepend(styleEl);
        
        // Add background rect
        const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bgRect.setAttribute('width', '100%');
        bgRect.setAttribute('height', '100%');
        bgRect.setAttribute('fill', '#ffffff');
        clonedSvg.insertBefore(bgRect, styleEl.nextSibling);
        
        // Serialize SVG to string
        const svgData = new XMLSerializer().serializeToString(clonedSvg);
        
        // Cleanup container
        document.body.removeChild(container);
        
        // Convert SVG to PNG using canvas for better compatibility
        console.log("[Infographic Image] Converting SVG to PNG...");
        const pngBlob = await new Promise((resolve, reject) => {{
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const scale = 2; // Higher resolution for clarity
            canvas.width = Math.round(width * scale);
            canvas.height = Math.round(height * scale);
            
            // Fill white background
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.scale(scale, scale);
            
            const img = new Image();
            img.onload = () => {{
                ctx.drawImage(img, 0, 0, width, height);
                canvas.toBlob((blob) => {{
                    if (blob) {{
                        resolve(blob);
                    }} else {{
                        reject(new Error('Canvas toBlob failed'));
                    }}
                }}, 'image/png');
            }};
            img.onerror = (e) => reject(new Error('Failed to load SVG as image: ' + e));
            img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
        }});
        
        const file = new File([pngBlob], `infografika-${{uniqueId}}.png`, {{ type: 'image/png' }});
        
        // Upload file to OpenWebUI API
        console.log("[Infographic Image] Uploading PNG file...");
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
            throw new Error(`Upload failed: ${{uploadResponse.statusText}}`);
        }}
        
        const fileData = await uploadResponse.json();
        const fileId = fileData.id;
        const imageUrl = `/api/v1/files/${{fileId}}/content`;
        
        console.log("[Infographic Image] PNG file uploaded, ID:", fileId);
        
        // Generate markdown image with file URL
        const markdownImage = `![📊 Infografika](${{imageUrl}})`;
        
        // Update message via API
        if (chatId && messageId) {{
            
            // Helper function with retry logic
            const fetchWithRetry = async (url, options, retries = 3) => {{
                for (let i = 0; i < retries; i++) {{
                    try {{
                        const response = await fetch(url, options);
                        if (response.ok) return response;
                        if (i < retries - 1) {{
                            console.log(`[Infographic Image] Retry ${{i + 1}}/${{retries}} for ${{url}}`);
                            await new Promise(r => setTimeout(r, 1000 * (i + 1)));
                        }}
                    }} catch (e) {{
                        if (i === retries - 1) throw e;
                        await new Promise(r => setTimeout(r, 1000 * (i + 1)));
                    }}
                }}
                return null;
            }};
            
            // Get current chat data
            const getResponse = await fetch(`/api/v1/chats/${{chatId}}`, {{
                method: "GET",
                headers: {{ "Authorization": `Bearer ${{token}}` }}
            }});
            
            if (!getResponse.ok) {{
                throw new Error("Failed to get chat data: " + getResponse.status);
            }}
            
            const chatData = await getResponse.json();
            let updatedMessages = [];
            let newContent = "";
            
            if (chatData.chat && chatData.chat.messages) {{
                updatedMessages = chatData.chat.messages.map(m => {{
                    if (m.id === messageId) {{
                        const originalContent = m.content || "";
                        // Remove existing infographic images
                        const infographicPattern = /\\n*!\\[📊[^\\]]*\\]\\((?:data:image\\/[^)]+|(?:\\/api\\/v1\\/files\\/[^)]+))\\)/g;
                        let cleanedContent = originalContent.replace(infographicPattern, "");
                        cleanedContent = cleanedContent.replace(/\\n{{3,}}/g, "\\n\\n").trim();
                        // Append new image
                        newContent = cleanedContent + "\\n\\n" + markdownImage;
                        
                        // Update history object as well
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
                console.warn("[Infographic Image] Could not find message to update");
                return;
            }}
            
            // Try to update frontend display via event API
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
                console.log("[Infographic Image] Event API not available, continuing...");
            }}
            
            // Persist to database
            const updatePayload = {{
                chat: {{
                    ...chatData.chat,
                    messages: updatedMessages
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
                console.log("[Infographic Image] ✅ Message persisted successfully!");
            }} else {{
                console.error("[Infographic Image] ❌ Failed to persist message after retries");
            }}
        }} else {{
            console.warn("[Infographic Image] ⚠️ Missing chatId or messageId, cannot persist");
        }}
        
    }} catch (error) {{
        console.error("[Infographic Image] Error:", error);
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
        logger.info("Action: Infographic started (v1.4.0)")

        # Get user information
        if isinstance(__user__, (list, tuple)):
            user_language = __user__[0].get("language", "cs") if __user__ else "cs"
            user_name = __user__[0].get("name", "Uživatel") if __user__[0] else "Uživatel"
            user_id = (
                __user__[0]["id"]
                if __user__ and "id" in __user__[0]
                else "unknown_user"
            )
        elif isinstance(__user__, dict):
            user_language = __user__.get("language", "cs")
            user_name = __user__.get("name", "Uživatel")
            user_id = __user__.get("id", "unknown_user")

        # Get current time
        now = datetime.now()
        current_date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        current_year = now.strftime("%Y")

        original_content = ""
        try:
            messages = body.get("messages", [])
            if not messages:
                raise ValueError("Nelze získat platný obsah uživatelské zprávy.")

            # Get last N messages based on MESSAGE_COUNT
            message_count = min(self.valves.MESSAGE_COUNT, len(messages))
            recent_messages = messages[-message_count:]

            # Aggregate content from selected messages with labels
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
                raise ValueError("Nelze získat platný obsah uživatelské zprávy.")

            original_content = "\n\n---\n\n".join(aggregated_parts)

            # Extract non-HTML text
            parts = re.split(r"```html.*?```", original_content, flags=re.DOTALL)
            long_text_content = ""
            if parts:
                for part in reversed(parts):
                    if part.strip():
                        long_text_content = part.strip()
                        break

            if not long_text_content:
                long_text_content = original_content.strip()

            # Check text length
            if len(long_text_content) < self.valves.MIN_TEXT_LENGTH:
                short_text_message = f"Text je příliš krátký ({len(long_text_content)} znaků). Pro analýzu zadejte alespoň {self.valves.MIN_TEXT_LENGTH} znaků."
                await self._emit_notification(
                    __event_emitter__, short_text_message, "warning"
                )
                return {
                    "messages": [
                        {"role": "assistant", "content": f"⚠️ {short_text_message}"}
                    ]
                }

            await self._emit_notification(
                __event_emitter__, "📊 Infografika spuštěna, generuji...", "info"
            )
            await self._emit_status(
                __event_emitter__,
                "📊 Infografika: Zahájení generování...",
                False,
            )

            # Generate unique ID
            unique_id = f"id_{int(time.time() * 1000)}"

            # Build prompt
            await self._emit_status(
                __event_emitter__,
                "📊 Infografika: Analyzuji obsah přes AI...",
                False,
            )
            formatted_user_prompt = USER_PROMPT_GENERATE_INFOGRAPHIC.format(
                user_name=user_name,
                current_date_time_str=current_date_time_str,
                user_language=user_language,
                long_text_content=long_text_content,
            )

            # Determine model to use
            target_model = self.valves.MODEL_ID
            if not target_model:
                target_model = body.get("model")

            llm_payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_INFOGRAPHIC_ASSISTANT},
                    {"role": "user", "content": formatted_user_prompt},
                ],
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
                raise ValueError("Neplatný formát odpovědi LLM nebo prázdná odpověď.")

            await self._emit_status(
                __event_emitter__,
                "📊 Infografika: AI analýza hotová, parsování syntaxe...",
                False,
            )

            assistant_response_content = llm_response["choices"][0]["message"][
                "content"
            ]
            infographic_syntax = self._extract_infographic_syntax(
                assistant_response_content
            )

            # Prepare content components
            await self._emit_status(
                __event_emitter__,
                "📊 Infografika: Vykresluji graf...",
                False,
            )
            content_html = (
                CONTENT_TEMPLATE_INFOGRAPHIC.replace("{unique_id}", unique_id)
                .replace("{user_name}", user_name)
                .replace("{current_date_time_str}", current_date_time_str)
                .replace("{current_year}", current_year)
                .replace("{infographic_syntax}", infographic_syntax)
            )

            # Replace placeholder first, then convert {{ to { and }} to }
            script_html = SCRIPT_TEMPLATE_INFOGRAPHIC.replace("{unique_id}", unique_id)
            script_html = script_html.replace("{{", "{").replace("}}", "}")

            # Extract existing HTML if any
            existing_html_block = ""
            match = re.search(
                r"```html\s*(<!-- OPENWEBUI_PLUGIN_OUTPUT -->[\s\S]*?)```",
                original_content,
            )
            if match:
                existing_html_block = match.group(1)

            if self.valves.CLEAR_PREVIOUS_HTML:
                original_content = self._remove_existing_html(original_content)
                final_html = self._merge_html(
                    "",
                    content_html,
                    CSS_TEMPLATE_INFOGRAPHIC,
                    script_html,
                    user_language,
                )
            else:
                if existing_html_block:
                    original_content = self._remove_existing_html(original_content)
                    final_html = self._merge_html(
                        existing_html_block,
                        content_html,
                        CSS_TEMPLATE_INFOGRAPHIC,
                        script_html,
                        user_language,
                    )
                else:
                    final_html = self._merge_html(
                        "",
                        content_html,
                        CSS_TEMPLATE_INFOGRAPHIC,
                        script_html,
                        user_language,
                    )

            # Check output mode
            if self.valves.OUTPUT_MODE == "image":
                # Image mode: use JavaScript to render and embed as Markdown image
                chat_ctx = self._get_chat_context(body, __metadata__)
                chat_id = chat_ctx["chat_id"]
                message_id = chat_ctx["message_id"]

                await self._emit_status(
                    __event_emitter__,
                    "📊 Infografika: Generuji obrázek...",
                    False,
                )

                if __event_call__:
                    js_code = self._generate_image_js_code(
                        unique_id=unique_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        infographic_syntax=infographic_syntax,
                    )

                    await __event_call__(
                        {
                            "type": "execute",
                            "data": {"code": js_code},
                        }
                    )

                await self._emit_status(
                    __event_emitter__, "✅ Infografika: Obrázek vygenerován!", True
                )
                await self._emit_notification(
                    __event_emitter__,
                    f"📊 Infografika vygenerována, {user_name}!",
                    "success",
                )
                logger.info("Infographic generation completed in image mode")
                return body

            # HTML mode (default): embed as HTML block
            html_embed_tag = f"```html\n{final_html}\n```"
            body["messages"][-1]["content"] = f"{original_content}\n\n{html_embed_tag}"

            await self._emit_status(
                __event_emitter__, "✅ Infografika: Hotovo!", True
            )
            await self._emit_notification(
                __event_emitter__,
                f"📊 Infografika vygenerována, {user_name}!",
                "success",
            )
            logger.info("Infographic generation completed")

        except Exception as e:
            error_message = f"Zpracování infografiky selhalo: {str(e)}"
            logger.error(f"Infographic error: {error_message}", exc_info=True)
            user_facing_error = f"Infografika narazila na chybu při zpracování: {str(e)}.\nZkontrolujte backend logy Open WebUI pro více detailů."
            body["messages"][-1][
                "content"
            ] = f"{original_content}\n\n❌ **Chyba:** {user_facing_error}"

            await self._emit_status(
                __event_emitter__, "❌ Infografika: Generování selhalo", True
            )
            await self._emit_notification(
                __event_emitter__,
                f"❌ Generování infografiky selhalo, {user_name}!",
                "error",
            )

        return body
