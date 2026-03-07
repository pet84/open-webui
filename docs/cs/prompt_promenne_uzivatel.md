# Proměnné pro aktuálního uživatele (prompt variables)

Proměnné, které Open WebUI automaticky nahrazuje v promptech, system promptech a šablonách. Používají se ve formátu `{{NAZEV}}` (dvojité složené závorky, velká písmena).

---

## Uživatel

| Proměnná | Popis | Příklad |
|----------|-------|---------|
| `{{USER_NAME}}` | Jméno přihlášeného uživatele | Petr Novák |
| `{{USER_EMAIL}}` | E-mail uživatele | petr@example.com |
| `{{USER_LOCATION}}` | Lokace uživatele | Vyžaduje zapnutí v Settings → Interface |
| `{{USER_LANGUAGE}}` | Jazyk uživatele (locale) | cs-CZ, en-US |
| `{{USER_BIO}}` | Bio uživatele | *(pokud vyplněno)* |
| `{{USER_AGE}}` | Věk uživatele | *(pokud vyplněno)* |
| `{{USER_BIRTH_DATE}}` | Datum narození | *(pokud vyplněno)* |
| `{{USER_GENDER}}` | Pohlaví | *(pokud vyplněno)* |

---

## Datum a čas

| Proměnná | Popis | Příklad |
|----------|-------|---------|
| `{{CURRENT_DATE}}` | Aktuální datum | 2026-03-02 |
| `{{CURRENT_TIME}}` | Aktuální čas | 14:30 |
| `{{CURRENT_DATETIME}}` | Datum a čas dohromady | 2026-03-02 14:30:45 |
| `{{CURRENT_WEEKDAY}}` | Den v týdnu | pondělí |
| `{{CURRENT_TIMEZONE}}` | Časová zóna uživatele | Europe/Prague |

---

## Další

| Proměnná | Popis |
|----------|-------|
| `{{CLIPBOARD}}` | Obsah schránky (clipboard) |
| `{{prompt}}` | Celý text promptu uživatele |
| `{{prompt:start:N}}` | Prvních N znaků promptu |
| `{{prompt:end:N}}` | Posledních N znaků promptu |
| `{{prompt:middletruncate:N}}` | Prompt zkrácený na N znaků s `...` uprostřed |

---

## Použití

V **promptech**, **system promptech** a **šablonách** (např. generování titulku):

```
Ahoj {{USER_NAME}}! Dnes je {{CURRENT_DATE}}, {{CURRENT_WEEKDAY}}.
```

V **Actions** a **Filters** (Python) se kontext uživatele předává přes `__user__`:

```python
user_name = __user__.get("name", "User")
user_language = __user__.get("language", "cs-CZ")
# Datum: datetime.now().strftime("%d. %m. %Y %H:%M")
```

---

## Poznámka

- **Časová zóna:** Datum a čas mohou používat zónu serveru nebo uživatele (závisí na nastavení).
- **Formát:** Vždy `{{NAZEV}}` – velká písmena, dvojité složené závorky.
- **User location:** `{{USER_LOCATION}}` vyžaduje zapnutí v Settings → Interface a HTTPS.
