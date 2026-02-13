"""
title: Google Gemini Pipeline
author: owndev, olivier-lacroix
author_url: https://github.com/owndev/
project_url: https://github.com/owndev/Open-WebUI-Functions
funding_url: https://github.com/sponsors/owndev
version: 1.11.0
required_open_webui_version: 0.6.26
license: Apache License 2.0
description: Vysoce optimalizovaný Google Gemini pipeline s pokročilými schopnostmi generování obrázků, inteligentní kompresí a zjednodušenými pracovními postupy zpracování.
features:
  - Optimalizované asynchronní API volání pro maximální výkon
  - Inteligentní cache modelů s konfigurovatelným TTL
  - Zjednodušená dynamická specifikace modelů s automatickým zpracováním prefixů
  - Chytré zpracování streamovaných odpovědí s bezpečnostními kontrolami
  - Pokročilá podpora multimodálních vstupů (text a obrázky)
  - Sjednocené generování a úprava obrázků s Gemini 2.5 Flash Image Preview
  - Inteligentní optimalizace obrázků s algoritmy komprese zohledňujícími velikost
  - Automatické nahrávání obrázků do Open WebUI s robustní podporou fallbacku
  - Optimalizované text-to-image a image-to-image pracovní postupy
  - Ne-streamovací režim pro generování obrázků pro prevenci přetečení chunků
  - Postupné aktualizace stavu pro optimální uživatelský zážitek
  - Konsolidované zpracování chyb a komplexní logování
  - Bezproblémová integrace Google Generative AI a Vertex AI
  - Pokročilé parametry generování (teplota, max tokeny, atd.)
  - Konfigurovatelné bezpečnostní nastavení s podporou proměnných prostředí
  - Vojenská úroveň šifrovaného ukládání citlivých API klíčů
  - Inteligentní grounding s integrací Google vyhledávání
  - Vertex AI Search grounding pro RAG
  - Nativní podpora volání nástrojů s automatickou správou podpisů
  - URL kontext grounding pro specifikované webové stránky
  - Sjednocené zpracování obrázků s konsolidovanými pomocnými metodami
  - Optimalizované vytváření payloadů pro modely generování obrázků
  - Konfigurovatelné parametry zpracování obrázků (velikost, kvalita, komprese)
  - Flexibilní možnosti fallbacku nahrávání a kontroly optimalizace
  - Konfigurovatelné úrovně myšlení (nízká/vysoká) pro modely Gemini 3
  - Konfigurovatelné rozpočty myšlení (0-32768 tokenů) pro modely Gemini 2.5
  - Konfigurovatelný poměr stran generování obrázků (1:1, 16:9, atd.) a rozlišení (1K, 2K, 4K)
  - Whitelist modelů pro filtrování dostupných modelů
  - Dodatečná podpora modelů pro modely nepodporované SDK
"""

# ============================================
# VLOŽ SEM CELÝ KÓD Z ORIGINÁLU
# ============================================
# 
# Kód najdeš v Open WebUI:
# 1. Jdi do Admin Panel → Functions
# 2. Najdi "Google Gemini Pipeline"
# 3. Klikni na ikonu klíče 🔑 nebo "Edit"
# 4. Zkopíruj celý kód (Ctrl+A, Ctrl+C)
# 5. Vlož sem (Ctrl+V)
#
# Nebo použij GitHub:
# https://github.com/owndev/Open-WebUI-Functions
#
# ============================================

# ============================================
# API key not valid / encrypted key sent to Google
# ============================================
#
# Chyba: "API key not valid" nebo v logu header 'x-goog-api-key': 'encrypted:gAAAAAB...'
#
# Klíč se ukládá zašifrovaně (EncryptedStr). K dešifrování se používá WEBUI_SECRET_KEY.
# Pokud je klíč po dešifrování stále "encrypted:...", znamená to, že dešifrování selhalo
# (jiný nebo chybějící WEBUI_SECRET_KEY) a Google dostane neplatný řetězec.
#
# Řešení (stačí jedno):
# 1. Nastav WEBUI_SECRET_KEY v prostředí kontejneru na stejnou hodnotu jako při
#    prvním uložení klíče v pipeline (nebo při startu instance).
# 2. Nebo v Admin → Functions → Google Gemini Pipeline → ikona ozubeného kolečka (Settings):
#    smaž pole API klíče a zadej znovu svůj čistý Google AI API klíč a ulož.
#    Ten se znovu zašifruje aktuálním WEBUI_SECRET_KEY.
#
# ============================================
# 404 Model not found (Open WebUI 0.8+)
# ============================================
#
# Když se pipeline vůbec neobjeví jako model (404: Model not found):
#
# 1. **Funkce se po chybě automaticky vypne**
#    V 0.8 při jakékoli chybě při načtení kódu pipeline (exec/import) Open WebUI
#    nastaví funkci na is_active=False. Pak se nebere do get_functions_by_type("pipe", active_only=True)
#    a její modely se nevrátí v /api/models → 404.
#
# 2. **Co udělat**
#    - Admin Panel → Functions → najdi „Google Gemini Pipeline“.
#    - Zkontroluj, že je **Active** zapnuté (zelené). Pokud ne, zapni to a ulož.
#    - Obnov seznam modelů (refresh v chatu nebo restart backendu).
#
# 3. **Když se po zapnutí zase vypne**
#    Při načtení stránky nebo refreshi modelů se pipeline znovu načte. Pokud načtení
#    selže (exception v kódu nebo v importech), funkce se znovu deaktivuje.
#    - V logu backendu hledej: „Error loading module: <id>: …“ a konkrétní chybu.
#    - Oprav kód pipeline (např. upload → upload_file_handler viz docs/cs/gemininy)
#      a v Admin → Functions vlož opravený kód a ulož.
#
# 4. **Oprava uploadu v 0.8**
#    V kódu pipeline musí být:
#      from open_webui.routers.files import upload_file_handler
#    a volání upload_file_handler(..., db=None), ne upload_file().
#    Viz soubor docs/cs/gemininy (nebo aktuální verze v Admin).
#
# ============================================
