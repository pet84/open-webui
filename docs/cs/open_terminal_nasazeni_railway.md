# Open Terminal – nasazení jako druhá služba na Railway

Open Terminal je **samostatná služba**. Open WebUI (Airis Chat) se k ní pouze **připojuje** přes URL a API klíč. V chatu pak máte prohlížení souborů, terminál a nástroje (read_file, write_file, list_dir, …).

## Architektura

- **Služba 1:** Airis Chat (Open WebUI) – už máte na Railway, `chat3.archenergy.cz`
- **Služba 2:** Open Terminal – nová služba na Railway s **vlastním volume** (persistentní `/home/user`)

WebUI neběží Open Terminal uvnitř sebe; pouze volá jeho API. Proto je potřeba Open Terminal nasadit zvlášť.

---

## 1. Nasazení Open Terminal na Railway

### 1.1 Nová služba z Docker image

1. V Railway projektu (kde máte Airis Chat 3.0) klikněte **+ New** → **Empty Service** (nebo **Deploy from GitHub** pokud budete mít fork).
2. Pro nejjednodušší variantu:
   - **Settings** nové služby → **Source**:
     - Zvolte **Docker Image** (pokud Railway nabízí).
     - Image: `ghcr.io/open-webui/open-terminal:v0.11.30` (aktuální stabilní; `latest` také funguje)
   - Pokud Railway umí jen „Deploy from GitHub“:
     - Forkujte [open-webui/open-terminal](https://github.com/open-webui/open-terminal), připojte repo k Railway a nasaďte (build z Dockerfile).

### 1.2 Proměnné prostředí

V **Variables** služby Open Terminal nastavte:

| Proměnná | Hodnota | Poznámka |
|----------|---------|----------|
| `OPEN_TERMINAL_API_KEY` | např. dlouhý náhodný řetězec | Vygenerujte (např. `openssl rand -hex 32`). Stejný klíč pak zadáte do WebUI. |

Pokud klíč **nastavíte**, používejte ho při připojování z WebUI. Pokud ho **nenastavíte**, Open Terminal ho vygeneruje sám – pak ho zjistíte z logů konteineru (`railway logs` nebo v Railway dashboardu).

### 1.2.1 Důležité: Port pro Railway

Railway vstřikuje proměnnou `PORT` (typicky 8080). Open Terminal standardně poslouchá na 8000 – bez úpravy dostanete **502 Bad Gateway**.

**Řešení:** V Railway → Settings → **Deploy** (nebo **Custom Start Command**) nastavte startovací příkaz:

```
open-terminal run --port ${PORT:-8000}
```

Nebo upravte ve forku `pet84/open-terminal` soubor `entrypoint.sh` – před `exec open-terminal "$@"` přidejte např.:

```bash
export PORT=${PORT:-8000}
exec open-terminal run --port $PORT
```

(Pokud entrypoint předává argumenty, upravte podle potřeby.)

### 1.3 Volume (persistentní soubory)

- V Railway přidejte k službě **Volume**.
- Připojte ho do cesty: **`/home/user`** (v dokumentaci Open Terminalu je to výchozí pracovní adresář v konteineru).
- Bez volume by se soubory v terminálu po restartu smazaly.

### 1.4 Doména a port

- **Port:** Open Terminal v konteineru poslouchá na **8000**.
- V Railway nastavte, že služba exponuje port **8000** (většinou automaticky z Dockerfile).
- V **Settings** služby přidejte **Public Networking** / **Generate domain** – dostanete URL typu `https://open-terminal-xxx.up.railway.app`.

Tuto **URL** si poznamenejte (bez koncového lomítka), budete ji dávat do WebUI.

---

## 2. Propojení v Open WebUI (Airis Chat)

1. Přihlaste se do **Airis Chat** jako admin (`chat3.archenergy.cz`).
2. **Admin Panel** (ikona ozubeného kolečka) → **Settings** → **Integrations**.
3. Sekce **Open Terminal** → **Add Connection** (nebo „Přidat připojení“).
4. Vyplňte:
   - **URL:** plná adresa vaší Open Terminal služby na Railway, např. `https://open-terminal-xxx.up.railway.app` (bez `/` na konci).
   - **API Key:** stejná hodnota jako `OPEN_TERMINAL_API_KEY` na Railway.
   - **Name:** volitelně např. „Railway Terminal“.
5. Uložte (**Save**).

Uživatelé pak v chatu uvidí terminál / prohlížeč souborů a budou moci používat nástroje Open Terminal (prohlížení, upload, editace, příkazy).

---

## 3. Ověření

- V chatu otevřete postranní panel souborů / terminálu (podle UI vaší verze WebUI).
- Pokud je připojení v pořádku, uvidíte adresářovou strukturu z Open Terminal instance (obsah `/home/user` z konteineru).
- V logách Open Terminal služby na Railway by neměly být 4xx/5xx chyby při přístupu z WebUI.

---

## 4. Shrnutí

| Krok | Kde | Co |
|------|-----|-----|
| 1 | Railway | Nová služba z image `ghcr.io/open-webui/open-terminal:v0.11.30` (nebo deploy z GitHubu). |
| 2 | Railway | Variable `OPEN_TERMINAL_API_KEY` (vygenerovat a uložit). |
| 3 | Railway | Volume připojený na `/home/user`. |
| 4 | Railway | Veřejná doména pro službu (port 8000). |
| 5 | WebUI Admin → Integrations | Přidat Open Terminal: URL + stejný API key. |

Open Terminal tak běží jako **druhá služba s vlastním volume** na Railway a WebUI k ní pouze přistupuje přes HTTPS a API klíč.

---

## 5. Novinky v 0.8.8 (WebSocket proxy, feature toggle)

Od Open WebUI 0.8.8 přibyly vylepšení pro interaktivní terminál:
- **WebSocket proxy** – spolehlivější připojení za Railway/proxy (automaticky)
- **Feature toggle** – povolení/zakázání interaktivního shellu na terminálovém serveru
- **Přesouvání souborů** drag & drop, **náhled HTML** souborů

Více viz **[open_terminal_0.8.8_novinky.md](./open_terminal_0.8.8_novinky.md)**.
