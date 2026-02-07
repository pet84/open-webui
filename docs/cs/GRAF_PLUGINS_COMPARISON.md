# 📊 Porovnání pluginů pro grafy

## Přehled

V Open WebUI máme **2 různé pluginy pro vytváření grafů**:

1. **Make charts out of your data** (Action) - Omar EL HACHIMI
2. **ChartJS** (Tool) - myria

---

## 🔄 Hlavní rozdíly

| Vlastnost | Make charts (Plotly) | ChartJS |
|-----------|----------------------|---------|
| **Typ** | **Action** (tlačítko) | **Tool** (AI volá funkci) |
| **Knihovna** | Plotly.js | Chart.js |
| **Jak se aktivuje** | Klikneš na tlačítko v chatu | AI automaticky zavolá funkci |
| **Vyžaduje API klíč** | ✅ Ano (OpenAI/Claude) | ❌ Ne |
| **Automatické barvy** | ❌ Ne (generuje AI) | ✅ Ano (HSL paleta) |
| **Dark/Light theme** | ❌ Ne | ✅ Ano (toggle tlačítko) |
| **Download PNG** | ✅ Ano (Plotly) | ✅ Ano (Chart.js) |
| **Typy grafů** | Všechny Plotly typy | line, bar, pie, doughnut, radar, polarArea |

---

## 📋 Detailní srovnání

### 1️⃣ Make charts out of your data (Action)

**Jak funguje:**
1. Napíšeš zprávu s daty (např. "Vytvoř graf prodejů: Q1=100, Q2=150, Q3=200")
2. Klikneš na tlačítko **"Make charts"** v chatu
3. Plugin pošle data do **OpenAI/Claude API**
4. AI analyzuje data a vygeneruje **HTML kód s Plotly grafem**
5. Graf se zobrazí v chatu

**Výhody:**
- ✅ **Inteligentní výběr typu grafu** - AI rozhodne, který typ je nejlepší
- ✅ **Flexibilní** - Podporuje všechny Plotly typy (3D, heatmap, scatter, atd.)
- ✅ **Automatická analýza dat** - AI rozumí kontextu a vybere vhodný graf

**Nevýhody:**
- ❌ **Vyžaduje API klíč** (OpenAI/Claude) - stojí peníze
- ❌ **Pomalejší** - musí volat externí API
- ❌ **Závisí na kvalitě AI** - někdy může vybrat špatný typ grafu

**Kdy použít:**
- Když máš nestrukturovaná data v textu
- Když chceš, aby AI automaticky vybralo typ grafu
- Když potřebuješ pokročilé Plotly grafy (3D, heatmap, atd.)

---

### 2️⃣ ChartJS (Tool)

**Jak funguje:**
1. Napíšeš dotaz (např. "Vytvoř graf prodejů za Q1-Q4")
2. **AI automaticky rozpozná**, že potřebuje graf
3. AI zavolá funkci: `chartjs(labels=["Q1","Q2","Q3","Q4"], datasets=[...])`
4. Plugin vygeneruje **HTML s Chart.js grafem**
5. Graf se zobrazí v chatu

**Výhody:**
- ✅ **Automatické** - AI to zavolá samo, nemusíš klikat
- ✅ **Rychlé** - žádné externí API volání
- ✅ **Zdarma** - nevyžaduje API klíč
- ✅ **Dark/Light theme** - přepínání jedním klikem
- ✅ **Automatické barvy** - HSL paleta, vždy vypadá dobře

**Nevýhody:**
- ❌ **Omezené typy grafů** - jen základní (line, bar, pie, atd.)
- ❌ **Musíš strukturovat data** - AI musí rozumět datům v dotazu
- ❌ **Závisí na AI** - pokud AI nerozpozná potřebu grafu, nezavolá funkci

**Kdy použít:**
- Když máš strukturovaná data (tabulky, seznamy)
- Když chceš rychlý a jednoduchý graf
- Když nechceš platit za API volání
- Když chceš dark/light theme toggle

---

## 🎯 Který použít?

### Použij **Make charts (Plotly)**, když:
- 📊 Potřebuješ pokročilé grafy (3D, heatmap, scatter plots)
- 🤖 Chceš, aby AI automaticky vybralo typ grafu
- 📝 Máš nestrukturovaná data v textu
- 💰 Máš API klíč a nezáleží ti na nákladech

### Použij **ChartJS**, když:
- ⚡ Chceš rychlý a jednoduchý graf
- 🎨 Chceš dark/light theme toggle
- 💵 Nechceš platit za API volání
- 📋 Máš strukturovaná data (tabulky, seznamy)
- 🤖 Chceš, aby AI automaticky rozpoznalo potřebu grafu

---

## 💡 Tip

**Můžeš použít oba současně!**
- ChartJS pro rychlé, jednoduché grafy
- Make charts pro pokročilé, komplexní vizualizace

---

## 📚 Technické detaily

### Make charts (Plotly)
- **Autor:** Omar EL HACHIMI
- **Knihovna:** Plotly.js (CDN)
- **API:** OpenAI/Claude (pro generování HTML)
- **Ukládání:** HTML soubory do `action_embed/`
- **Konfigurace:** `OPENIA_KEY`, `OPENIA_URL`

### ChartJS
- **Autor:** myria
- **Knihovna:** Chart.js (CDN)
- **API:** Žádné (lokální generování)
- **Ukládání:** Inline HTML v chatu
- **Konfigurace:** Valves (výška, šířka, barvy témat)

---

**Soubor:** `docs/cs/GRAF_PLUGINS_COMPARISON.md`
