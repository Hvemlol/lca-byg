# lca-byg — EPD extraction tool (starting point)

Desktop app that extracts structured data from Environmental Product
Declaration (EPD) PDFs via an LLM and stores it in a local SQLite database.

## Setup

```bash
pip install -r requirements.txt
```

The OpenAI API key is configured inside the app (Settings button) and stored
in the OS keyring. Alternatively, set the `OPENAI_API_KEY` environment
variable.

## Usage

```bash
# Graphical interface (EPD library, PDF import with review, settings)
python gui.py

# Command line (no GUI)
python main.py path/to/epd.pdf
python main.py --list
```

The database lives at `~/.lca-byg/lca.db`.

## Flow

```
PDF -> pdfplumber (text) -> LLM via instructor/pydantic (EPDRecord)
    -> review dialog (edit/confirm/discard) -> SQLite (epds table)
```

- `gui.py` — PyQt6 desktop interface: EPD table with search, PDF import,
  review dialog, settings (API key via keyring). Extraction runs on a
  background thread so the UI stays responsive.
- `models.py` — Pydantic schema for an EPD record; doubles as the LLM output contract.
- `extract.py` — PDF text extraction + structured LLM call.
- `db.py` — SQLite schema and insert/list helpers.
- `pipeline.py` — `extract_pdf()` / `process_pdf()` tie the steps together.
- `main.py` — CLI entry point.
- `settings.py` — API key storage in the OS keyring.

## Known limitations

- Text-based extraction only: scanned/image-only PDFs fail with
  "No extractable text found". A vision-model fallback (PDF pages -> images ->
  GPT-4o/Claude vision) is the natural next step.
- Records are deduplicated on `epd_number` (`INSERT OR REPLACE`).
- No projects/calculation layer yet.
