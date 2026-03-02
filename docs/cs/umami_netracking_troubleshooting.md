# Umami netracking – kontrola a řešení

## 1. Ověření env proměnných

- **UMAMI_WEBSITE_ID** (ne MAMI_WEBSITE_ID) – ID webu z Umami dashboardu
- **UMAMI_SCRIPT_URL** – např. `https://umami-production-418b.up.railway.app/script.js`

## 2. Umami Dashboard

V Umami musí být přidaný web s URL, která odpovídá vaší doméně (např. `https://airis-chat.railway.app`). Jinak se data neukládají.

## 3. CSP (Content-Security-Policy)

Když máte nastavenou `CONTENT_SECURITY_POLICY`, musí umožnit:

- **script-src** – doména Umami skriptu (automaticky doplněno)
- **connect-src** – doména Umami serveru pro odesílání dat (automaticky doplněno)

## 4. Ad blocker

AdBlock, uBlock Origin a podobné blokují analytické skripty. Otestujte v anonymním okně nebo vypnutým blokováním reklam.

## 5. Kontrola v DevTools (F12)

- **Console** – chyby typu `blocked by CSP` nebo `Failed to load script`
- **Network** – zda se `script.js` stáhne (status 200)
- **Network** – zda proběhnou requesty na `/api/send` nebo podobné k Umami serveru

## 6. data-host-url (self-hosted)

Pro vlastní Umami instanci se do skriptu doplňuje `data-host-url`, aby data mířila na správný server. Kontrola: v DevTools → Elements zkontrolujte, že má skript atribut `data-host-url="https://umami-production-418b.up.railway.app"`.
