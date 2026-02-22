# Složka `local/` – naše skripty a pipeline

Tady máme **vlastní doplňky** k Open WebUI, které nepatří do kořene projektu ani do `docs/cs` (tam jsou jen návody v .md).

## Obsah

- **`google_gemini_pipeline.py`** – pipeline pro Google Gemini (chat, obrázky, RAG, grounding). Návod: `docs/cs/google_gemini_pipeline_navod.md`
- **`create_excel.py`** – skripty související s exportem do Excelu
- **`backup_data.ps1`** / **`backup_data.sh`** – zálohování dat
- **`reset_data.ps1`** / **`reset_data.sh`** – reset dat
- **`check_filtered.py`**, **`filter_models.py`** – utility pro filtry/modelů

## Konvence

- **`docs/cs/`** = pouze návody a dokumentace (`.md`).
- **`local/`** = naše skripty (`.py`, `.ps1`, `.sh`) a pipeline, které kopírujeme do Open WebUI nebo spouštíme ručně.
