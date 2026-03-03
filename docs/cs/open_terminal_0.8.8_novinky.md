# Open Terminal – novinky v Open WebUI 0.8.8

Přehled nových funkcí souvisejících s Open Terminal v Open WebUI v0.8.8.

---

## 1. WebSocket proxy pro interaktivní terminál

### Co to je

Nový endpoint v Open WebUI, který **proxy WebSocket spojení** z prohlížeče na Open Terminal server. Interaktivní terminál (živé psaní příkazů a výstup v reálném čase) tak funguje spolehlivěji i za reverse proxy (Railway, nginx, Cloudflare).

### Jak to funguje

```
PŘED 0.8.8:
  Prohlížeč --WebSocket--> Open Terminal (přímé)
  ❌ Často selhalo za proxy (WebSocket upgrade blokován)

OD 0.8.8:
  Prohlížeč --> Open WebUI (proxy) --> Open Terminal
  ✅ WebSocket prochází přes Open WebUI, proxy není problém
```

- **Automatické** – žádná konfigurace na vaší straně
- Prohlížeč se připojuje na Open WebUI (HTTPS/WebSocket), Open WebUI udržuje WebSocket k Open Terminal
- Živé psaní a výstup v reálném čase

### Kde to nastavovat

**Nikde.** Proxy je součástí Open WebUI 0.8.8, funguje automaticky po nasazení nové verze.

---

## 2. Přepínač funkce Open Terminal (feature toggle)

### Co to je

Administrátoři mohou na **Open Terminal serveru** povolit nebo zakázat **interaktivní terminál**. Uživatelé pak mají buď jen souborové operace (list_dir, read_file, write_file, run_command přes AI), nebo i živý shell.

### Kde to nastavovat

Konfigurace je na **terminálovém serveru** (Open Terminal), ne v Open WebUI.

| Kde | Co |
|-----|-----|
| **Open Terminal** (služba na Railway) | Env proměnná nebo config pro povolení/zakázání interaktivního terminálu |
| **Open WebUI** | Pouze připojení k terminálu – respektuje, co terminál nabízí |

Konkrétní název proměnné viz dokumentace [open-webui/open-terminal](https://github.com/open-webui/open-terminal). Typicky něco jako `ENABLE_INTERACTIVE_TERMINAL=true` (nebo podobně podle implementace).

### Proč to použít

- **Bezpečnost** – vypnout živý shell pro běžné uživatele, nechat jen AI nástroje
- **Kontrola** – rozhodnout, kdo smí psát příkazy přímo do terminálu

---

## 3. Další vylepšení v 0.8.8

- **Přesouvání souborů** – drag & drop v prohlížeči souborů (přesun mezi složkami)
- **Náhled HTML** – soubory `.html` se zobrazují v iframe s přepínačem preview/zdroják
- **Opravy** – nástroje Open Terminal fungují i při direct connection; správné zacházení s `null` parametry v tool calls

---

## 4. Shrnutí pro nasazení

| Akce | Kde |
|------|-----|
| **Nasadit Open WebUI 0.8.8** | Railway / váš hosting |
| **WebSocket proxy** | Automaticky v nové verzi |
| **Feature toggle** | Open Terminal server (env/config) |
| **Připojení terminálu** | Admin → Settings → Integrations → Open Terminal |

Po upgradu na 0.8.8 by měl interaktivní terminál fungovat spolehlivěji i za Railway proxy.
