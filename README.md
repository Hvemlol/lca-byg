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

## Projects and LCA calculation

The **Projects** tab holds construction projects. Each project has line
items referencing EPDs by quantity; the app computes per-line and total
GWP (modules A1-A3) as `quantity x gwp_a1_a3`:

```
projects(id, name, location, description, created_at)
line_items(id, project_id -> projects, epd_id -> epds, description, quantity)
```

- `projects_tab.py` — Projects tab: project list, line-item table,
  add/remove line items, running total.
- `db.py` — also holds project/line-item helpers and `project_total_gwp()`.

## Files

- `gui.py` — PyQt6 desktop interface: EPD tab (table with search, PDF
  import with review dialog) + Projects tab + settings (API key via
  keyring). Extraction runs on a background thread.
- `models.py` — Pydantic schema for an EPD record; doubles as the LLM output contract.
- `extract.py` — PDF text extraction + structured LLM call.
- `db.py` — SQLite schema (epds, projects, line_items) and helpers.
- `pipeline.py` — `extract_pdf()` / `process_pdf()` tie the steps together.
- `main.py` — CLI entry point.
- `settings.py` — API key storage in the OS keyring.

## Known limitations

- Text-based extraction only: scanned/image-only PDFs fail with
  "No extractable text found". A vision-model fallback (PDF pages -> images ->
  GPT-4o/Claude vision) is the natural next step.
- EPD re-imports update in place keyed on `epd_number` (row id preserved,
  so line-item references stay valid).
- No unit conversion yet: quantities must be entered in the EPD's declared
  unit (e.g. kg for rebar EPDs, m3 for concrete EPDs).
- Calculation covers GWP A1-A3 only; other impact categories and life
  cycle modules are not modeled yet.
- No report/export yet.
