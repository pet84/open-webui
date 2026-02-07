"""
title: Adaptive Memory v3.0 - Advanced Memory System for OpenWebUI
author: AG
description: Pokročilý systém pro persistentní, personalizovanou paměť pro LLM v OpenWebUI. Dynamicky extrahuje, filtruje, ukládá a načítá informace o uživatelích napříč konverzacemi.
"""

# ============================================
# VLOŽ SEM CELÝ KÓD Z ORIGINÁLU
# ============================================
# 
# Kód najdeš v Open WebUI:
# 1. Jdi do Admin Panel → Functions
# 2. Najdi "Adaptive Memory v3.0"
# 3. Klikni na ikonu klíče 🔑 nebo "Edit"
# 4. Zkopíruj celý kód (Ctrl+A, Ctrl+C)
# 5. Vlož sem (Ctrl+V)
#
# Nebo použij GitHub:
# https://github.com/owndev/Open-WebUI-Functions
# (hledej "Adaptive Memory" nebo "AG")
#
# ============================================
# 
# ============================================
# CO TO DĚLÁ A JAK FUNGUJE
# ============================================
#
# 🎯 HLAVNÍ ÚČEL:
# Umožňuje LLM "pamatovat si" informace o uživateli napříč různými konverzacemi.
# Bez tohoto pluginu AI "zapomíná" vše mezi jednotlivými chaty.
#
# 💡 PŘÍNOS:
# ✅ Personalizace: AI si pamatuje tvoje preference, jméno, cíle, vztahy
# ✅ Kontext: V každé nové konverzaci má AI přístup k relevantním informacím o tobě
# ✅ Přirozenost: Konverzace plynou přirozeněji, nemusíš pořád opakovat základní info
# ✅ Efektivita: Méně opakování, více produktivní komunikace
#
# 🔄 JAK FUNGUJE (3 HLAVNÍ FÁZE):
#
# 1️⃣ EXTRACTION (Extrakce):
#    - Když napíšeš zprávu, plugin analyzuje obsah pomocí LLM
#    - Identifikuje "zapamatovatelné" informace:
#      * Preference: "Mám rád kávu"
#      * Identity: "Jmenuji se Jan"
#      * Goals: "Chci se naučit Python"
#      * Relationships: "Mám sestru Marii"
#    - Filtruje trivia a obecné znalosti (neukládá "2+2=4")
#
# 2️⃣ STORAGE (Ukládání):
#    - Uloží extrahované informace do vektorové databáze
#    - Každá paměť má tagy (identity, preference, goal, atd.)
#    - Organizuje do "Memory Banks" (Personal, Work, General)
#    - Používá deduplikaci (neukládá stejné info dvakrát)
#
# 3️⃣ RETRIEVAL (Načítání):
#    - Před každou odpovědí AI hledá relevantní paměti
#    - Používá vektorovou podobnost (embedding) k nalezení souvisejících informací
#    - Volitelně používá LLM pro přesnější relevanci
#    - Vloží relevantní paměti do kontextu AI (jako "system message")
#
# 🧠 POKROČILÉ FUNKCE:
# - Clustering: Seskupuje podobné paměti a sumarizuje je (šetří místo)
# - Pruning: Automaticky odstraňuje staré/neaktualní paměti při překročení limitu
# - Error Guard: Dočasně vypne funkce při vysoké chybovosti
# - Background Tasks: Pravidelně čistí a optimalizuje paměť na pozadí
#
# ⚙️ KONFIGURACE:
# - Rozsáhlé "valves" pro jemné doladění
# - Možnost vypnout/zapnout jednotlivé kategorie paměti
# - Nastavení thresholdů pro relevanci a podobnost
# - Volba mezi FIFO a relevance-based pruning
#
# 📊 PŘÍKLAD:
# Konverzace 1: "Jmenuji se Jan a mám rád Python"
# → Plugin uloží: "User jmenuje se Jan" + "User má rád Python"
#
# Konverzace 2 (o týden později): "Jaký programovací jazyk bych měl učit?"
# → Plugin načte: "User má rád Python"
# → AI odpoví: "Měl bys učit Python, protože už ho máš rád!"
#
# ============================================
# TECHNICKÉ DETAILY
# ============================================
# - Typ: FILTER (běží v pipeline před i po LLM odpovědi)
# - Používá: sentence-transformers pro embedding
# - Databáze: Open WebUI Memories API
# - Optimalizace: Caching, lazy loading, batch processing
# 
# Před použitím si pečlivě prostuduj dokumentaci a konfiguraci!
# ============================================
