"""Fork patch (pet84 / Airis): česká hláška místo surové chyby poskytovatele, když dojde kredit.

Uživatelé dostávali anglické chyby typu „This request requires more credits…“ (OpenRouter 402),
„You exceeded your current quota…“ (OpenAI) nebo „Your project has exceeded its monthly spending cap“
(Google přes openai-compatible připojení) a nevěděli, že mají dát vědět Petrovi.
Stejné texty používají pipe funkce Googlu a filtr Limity AI v databázi.

Volá se ve třech cestách, kudy chyba poskytovatele končí v chatu: utils/middleware.py
(get_message_error_content + nestreamovaná odpověď) a main.py (chyba zpracování dotazu).
Původní text chyby se dál loguje (events.publish_model_provider_request_failed, log.error).
"""

_OPENROUTER = ('requires more credits', 'insufficient credits', 'exceed your available credits')
_OPENAI = ('insufficient_quota', 'exceeded your current quota', 'credit balance', 'credit_balance', 'billing_hard_limit')
_GOOGLE = ('spending cap', 'spend cap')

_KONTAKT = 'Dej prosím vědět Petrovi, ať ho dobije, aby to mohli dál používat všichni.'
_JINY_MODEL = 'Mezitím můžeš zkusit jiný model.'


def cesky_kredit(error):
    """Vrátí českou hlášku, pokud jde o došlý kredit; jinak chybu beze změny (str i dict)."""
    if isinstance(error, dict):
        text = str(error)
    elif isinstance(error, str):
        text = error
    else:
        return error
    t = text.lower()
    if any(p in t for p in _OPENROUTER):
        return f'💳 Došel kredit na OpenRouteru, takže teď nemůžu odpovědět. {_KONTAKT}'
    if any(p in t for p in _OPENAI):
        return f'💳 Došel kredit u OpenAI (modely GPT), takže teď nemůžu odpovědět. {_KONTAKT} {_JINY_MODEL}'
    if any(p in t for p in _GOOGLE):
        return (
            '💳 Došel měsíční kredit pro Google Gemini, na kterém tenhle model běží, takže teď nemůžu odpovědět. '
            f'Dej prosím vědět Petrovi, ať ho navýší, aby to mohli dál používat všichni. {_JINY_MODEL}'
        )
    return error
