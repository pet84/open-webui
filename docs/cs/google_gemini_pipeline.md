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
