# Změny forku pet84/open-webui (Airis Chat 3.0)

Technické poznámky k úpravám forku proti upstreamu Open WebUI – co se při merge řešilo a které patche se musí
zachovat. Uživatelský přehled novinek (česky) je v `CHANGELOG.md` v sekci „Co je nového“ – ten se ukazuje
v okně po aktualizaci, proto sem patří technika a tam lidská řeč.

## [0.12.2] - 2026-10-14

- Merge upstream v0.12.2 (tag), bez migrací.
- cs-CZ: 4038 klíčů, 2 nové přeloženy (Ponechat obojí v porovnání revizí), 100 %.
- Fork patche beze změny (allow-modals, cached_context, create_skill list[dict], iframe, Umami, google-genai, NODE_OPTIONS).

## [0.12.1] - 2026-10-14

- Merge upstream v0.12.1 (tag).
- cs-CZ: sloučeno s upstream (4036 klíčů), 126 nových textů přeloženo (Aplikace v kanálech, porovnání revizí, export .skill), terminologie forku zachována (100 %).
- Oprava VRM 0.x avatara: fork patch z 0.12.0 odstraněn, upstream to opravil sám (#32270) — obě opravy dohromady by se sčítaly a build by padal na dvojí `const mirror`.
- `package-lock.json` převzat z upstreamu (fork měl nekonzistentní `eol` 0.9.2 s odkazem na 0.9.1).
- Fork patche beze změny: tisk z náhledu artefaktu (`allow-modals`), `cached_context`, `create_skill`/`update_skill_files` s `list[dict]`, iframe cookies/CSP, Umami, CalendarSidebar i18n, UserMenu, `google-genai`, `NODE_OPTIONS`, idempotentní migrace `b7c8d9e0f1a2`.

## [0.12.0] - 2026-10-10

- Merge upstream v0.12.0 (tag).
- cs-CZ: sloučeno s upstream (3910 klíčů), 184 nových textů přeloženo, terminologie forku zachována (100 %).
- `google-genai==1.66.0` dál v `backend/requirements.txt` (pipe funkce Google).
- Fork patche beze změny: iframe cookies/CSP, Umami, CalendarSidebar i18n, UserMenu bez "Admin Settings", `NODE_OPTIONS` v Dockerfile.
- Oprava hlasového avatara: postavy VRM 0.x (většina z VRoid Hubu) stály s rukama nahoře — vestavěná póza teď převádí osy jako three-vrm-animation (`voice-avatar-renderer.ts`).
- Náhled artefaktu (boční panel) má v sandboxu i `allow-modals`, aby šel z HTML artefaktu vyvolat `window.print()` — tlačítko „Uložit jako PDF“ v prezentacích z dovednosti Prezentace ArchEnergy (`Artifacts.svelte`). Ctrl+P v náhledu tiskl celé okno Airisu.
- cs-CZ: popisek příkazu `/skills:create` už netvrdí „terminálová dovednost“ (terminál nepotřebuje).
- Oprava Google pipeline agentů (NZÚ boty, Google Notebook, Gemini): nové vestavěné nástroje `create_skill` a `update_skill_files` měly parametr typu `list[Pydantic model]`, který google-genai neumí převést → každá odpověď končila „Failed to parse the parameter operations". Parametry jsou teď `list[dict]` (validace zůstává v `Skills`).
- Nový vlastní parametr agenta `cached_context` (`{"url": …, "prefix": …}`): znalostní báze z URL se vloží úplně na začátek system promptu, u Claude přes OpenRouter se značkou `cache_control` (cache 5 min → opakované dotazy za ~desetinu). Řešeno v routeru (`utils/cached_context.py`), protože filtry a middleware přidávají text (datum s časem, paměť) na začátek systémové zprávy a slévají ji do řetězce. Pro NZÚ agenty na Claude Haiku.

## [0.11.4] - 2026-09-21

#### Added

- **Český překlad dorovnán na 100 %.** Upstream 0.11.4 rozšířil cs-CZ na 3552 klíčů a sám doplnil ~1900 dosud prázdných; fork přeložil zbylých 92 nových klíčů (porovnání souborů, obrázek na pozadí modelu, dovednosti z terminálu, vyhledávač Staan, nápovědné dotazy). Terminologie forku (Konverzace, Instrukce, Tvorba Agentů) zachována — 200 klíčů drží náš překlad před upstreamem.

#### Changed

- **Upstream merge 0.11.4** (327 commitů). **Žádné nové migrace** — upstream jen přepsal idempotentní `b7c8d9e0f1a2_add_last_read_at_to_chat.py` (převzato), schéma DB beze změny, záloha nebyla nutná. Migrační chain ověřen: jeden head `d4c1a8e37b62`, 58 revizí. Konflikty pouze v `main.py` (klíč `umami` + nový `i18n` v `/api/config`) a `cs-CZ/translation.json`.
- Fork patche ověřeny beze změny: Node heap 6144 v `Dockerfile` (upstream svůj `NODE_OPTIONS` zakomentoval — náš zůstává), iframe embedding (`env.py`, `security_headers.py`), Umami (`config.py`, `main.py`), `$i18n.t()` v kalendáři, `UserMenu.svelte` bez „Admin Settings", vlastní favicony, vypnuté upstream CI workflows.
- Obraz se dál staví bez `USE_SLIM` (standardní obraz; upstream ho zmenšil o ~170 MB).

#### Fixed

- **Vrácen balík `google-genai==1.66.0`** (`backend/requirements.txt`, `pyproject.toml`). Upstream 0.11.4 ho z obrazu vyhodil jako nepoužívaný, ale šest pipe funkcí Airisu (Google Gemini Pipeline, Google Notebook, NZÚ boty) ho importuje — po prvním nasazení 0.11.4 se při startu všechny samy deaktivovaly (`cannot import name 'genai' from 'google'`). Po opravě je nutné funkce v Administraci → Funkce znovu zapnout.

## [0.11.3] - 2026-08-31

#### Added

- **Doplněn český překlad (1 nový klíč).** „+{{COUNT}} more" → „+{{COUNT}} dalších". Pokrytí cs-CZ 2217/3122 (71 %).

#### Changed

- **Upstream merge 0.11.3** (11 commitů, 11 souborů — hotfix pár hodin po 0.11.2). **Žádné nové migrace**, schéma DB beze změny, záloha nebyla nutná. Migrační chain ověřen: jeden head `d4c1a8e37b62`, 58 revizí. Merge proběhl **bez jediného konfliktu**.
- Fork patche ověřeny beze změny: Node heap 6144 v `Dockerfile`, iframe embedding (`env.py`, `security_headers.py`), Umami (`config.py`, `main.py`), `$i18n.t()` v kalendáři, `UserMenu.svelte` bez „Admin Settings", vlastní favicony, vypnuté upstream CI workflows.

## [0.11.2] - 2026-08-31

#### Added

- **Doplněn český překlad (4 nové klíče).** 3119 → 3122 klíčů (upstream jeden klíč odstranil). Nově: „Režim přístupnosti", „Rodina písma" a nastavení lokálního písma rozhraní, hlášení o částečně neúspěšném nahrání souborů.

#### Changed

- **Upstream merge 0.11.2** (100 commitů, 175 souborů). **Žádné nové migrace** — schéma DB beze změny, zálohu nebylo nutné pořizovat. Migrační chain ověřen: jeden head `d4c1a8e37b62`, 58 revizí.
- Fork patche ověřeny beze změny: Node heap 6144 v `Dockerfile`, iframe embedding (`env.py`, `security_headers.py`), Umami (`config.py`, `main.py`), `$i18n.t()` v kalendáři, odstraněná položka „Admin Settings" v `UserMenu.svelte`, vlastní favicony, vypnuté upstream CI workflows.

## [0.11.1] - 2026-08-25

#### Added

- **Doplněn český překlad (111 nových klíčů).** 3024 → 3119 klíčů; pokrytí cs-CZ 2214/3119 (71 %). Nové oblasti: oprávnění nástrojů (Povolit/Zamítnout volání), správa lokálních modelů (LM Studio, stahování/načítání), terminál a sandbox iframe, Tika 3.x/4.x, přeindexování vektorů, výchozí nastavení rozhraní.

#### Changed

- **Upstream merge 0.11.1** (462 commitů). 3 nové migrace (`1ce6ade7d93b` index group_member.user_id, `6d09d1bf1f23` oprava dvojitě zakódovaného user OAuth, `d4c1a8e37b62` chat timer_at + indexy) — DB záloha pořízena před nasazením. Migrační chain ověřen: jeden head `d4c1a8e37b62`, 58 revizí.
- **Přihlašovací stránka převzata z upstreamu.** Fork měl vlastní (centrované) umístění loga; upstream k němu ve v0.11.1 doplnil licenční doložku, že se jeho sign-in logo nesmí měnit ani přesouvat. Kosmetická fork úprava proto zrušena a použita upstream verze.

#### Fixed

- **Anglické názvy měsíců a dnů v kalendáři.** Upstream znovu odstranil `$i18n.t()` u `miniMonthNames` (`CalendarSidebar.svelte`) a nově i u `DAY_NAMES` (`CalendarView.svelte`). Obojí vráceno, upstream velikosti písma (`0.6875rem`) zachovány.

## [0.11.0] - 2026-07-27

#### Added

- **Doplněn český překlad (611 nových klíčů).** v0.11.0 přineslo 611 nových i18n klíčů (2578 → 3024). Všechny byly přeloženy do češtiny — popisky admin nastavení, oprávnění, sub-agenti, proměnné konverzace, zhuštění kontextu, LDAP/OAuth, extrakce dokumentů, plurály (`_one/_few/_many/_other`). Pokrytí cs-CZ: 2112/3024 (69,8 %); zbylé prázdné klíče byly nepřeložené už před tímto vydáním. Terminologie sjednocena s forkem (Prompt → Instrukce, Chat → Konverzace, Workspace → Tvorba Agentů).

#### Changed

- **Upstream merge 0.11.0.** 616 commitů, kompletní redesign UI. **7 nových schema migrací** (chat message meta, user variables, chat variables, automation folder, current_message_id, memory covering index, unique normalized email) — DB záloha pořízena před nasazením.
- **`SecurityHeadersMiddleware` přepsán upstreamem na pure ASGI**; fork patch pro iframe embedding znovu aplikován (odstranění `X-Frame-Options` se nyní vyhodnocuje jednou v `__init__` jako `_strip_xframe`, konzistentně s cachovanými hlavičkami).

#### Fixed

- **Anglické názvy měsíců v mini kalendáři.** Upstream v0.11.0 odstranil `$i18n.t()` u `miniMonthNames` v `CalendarSidebar.svelte` (v0.10.2 ho ještě měl) bez náhrady — v českém UI by se měsíce zobrazovaly anglicky. Wrapper vrácen, upstream styl (`font-normal`) zachován.

## [0.10.2] - 2026-07-01

#### Changed

- **Upstream merge 0.10.2.** Pulled latest upstream into the Airis Chat 3.0 fork on 2026-07-01. Clean auto-merge, no conflicts. Contains a bugfix to the existing `b10670c03dd5` user-table migration (JSON conversion) — already applied on prod during the v0.10.1 deploy, so no new schema migration runs on the production DB. Fork-specific patches preserved (verified): WEBUI_NAME branding, iframe embedding cookies, Umami SPA tracker, idempotent `last_read_at` migration, Czech translations, `/backups/` gitignore.

## [0.10.1] - 2026-06-29

#### Changed

- **Upstream merge 0.10.0 + 0.10.1.** Pulled latest upstream into the Airis Chat 3.0 fork on 2026-06-29. Major release (352 commits): config reshaped to per-key DB rows (`3ff2c63645b8`), memory path/meta/type additions, chat-message context summary, valve encryption (`ENABLE_VALVE_ENCRYPTION`). Several schema migrations — DB backup taken before deploy. Fork-specific patches preserved: WEBUI_NAME branding, iframe embedding cookies (env.py), Umami SPA tracker (re-applied to the refactored main.py `/api/config`), idempotent `last_read_at` migration, Czech translations.

## [0.9.6] - 2026-06-01

#### Changed

- **Upstream merge 0.9.6.** Pulled latest upstream into the Airis Chat 3.0 fork on 2026-06-02. Massive upstream refactor (peewee migration layer deprecated, legacy table primary keys fixed, knowledge base directories, channels streaming agent, `ConfigVar` rename). Many DB migrations including legacy PK additions — DB backup taken before deploy. Fork-specific patches preserved: WEBUI_NAME branding, iframe embedding cookies (env.py), Umami SPA tracker, idempotent `last_read_at` migration, Czech translations.

## [0.9.5] - 2026-05-09

#### Changed

- **Upstream merge 0.9.5.** Pulled latest upstream into the Airis Chat 3.0 fork on 2026-05-11. Includes security hardening (redirect-based SSRF protection, mass-assignment fixes, public-sharing permission gating) and the new `IFRAME_CSP` env var. No new schema migrations. Fork-specific patches preserved: WEBUI_NAME branding, iframe embedding cookies, Umami SPA tracker, idempotent `last_read_at` migration, Czech translations.

## [0.9.4] - 2026-05-09

#### Changed

- **Upstream merge 0.9.3 + 0.9.4.** Pulled latest upstream releases into the Airis Chat 3.0 fork. Includes new schema migrations (pinned notes per user, memory user_id index) — DB backup taken before deploy. Fork-specific patches preserved: Czech translations, `WEBUI_NAME` branding, iframe embedding (auto `SameSite=None` + `Secure` cookies), Umami SPA tracker fix, idempotent `last_read_at` migration, Railway nightly redeploy workflow.

## [0.9.2] - 2026-04-24

#### Changed

- **Upstream:** Merged `open-webui/main` (0.9.x): scheduled automations, calendar workspace, task list in chat, async backend paths, DB migrations. Git tag `v0.9.2`. **Before deploying:** back up the database / `backend/data` volume (see `BACKUP_DATA.md`).

## [0.9.1] - 2026-04-21

#### Added

- **Railway nightly redeploy (GitHub Actions).** Scheduled workflow (`0 2 * * *` UTC) and manual dispatch to soft-restart the app on Railway via `railway redeploy`, plus optional `railway status --json` debug listing for service name/ID verification.

#### Changed

- **CI:** Railway `redeploy` uses current `@railway/cli` syntax (`--service` and `--yes` only); `RAILWAY_ENVIRONMENT` is passed as an environment variable instead of the unsupported `--environment` flag.
- **Fork branding:** When `WEBUI_NAME` is set, the UI no longer appends “(Open WebUI)” to the custom name.

#### Fixed

- **Umami analytics:** Load the tracker script so `document.currentScript` works correctly in the SPA.
