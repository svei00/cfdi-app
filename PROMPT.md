# CFDI Processor — App Specification & Build Prompt

> Reusable spec. Paste into any AI (Claude, GLM, ChatGPT, Gemini) so it
> understands the app without seeing the code or screenshots. Keep it updated as
> the app evolves.
>
> **⚠️ For the NEXT build phase (F2 — GUI stabilization & package restructure),
> the master document is `ROADMAP.md`** (bug diagnosis, full project phases,
> F2 architecture, recorded decisions). Read it first; this file is the
> product-level spec.

## Role
You are helping me build and extend a desktop application for Mexican electronic
invoicing (CFDI / SAT). I am a solo developer. I am Spanish-speaking; the SAT
domain terms stay in Spanish, code/comments can be either. Prioritize an
intuitive GUI — my users are accountants and small-business owners who dislike
command-line tools.

## What the app does TODAY (working; maturity: alpha)
A Python tool that:
1. Lets the user pick a folder of CFDI XML files (and/or .zip archives of XMLs).
2. Walks the folder, auto-detects each XML's CFDI version and document type.
3. Parses each file into a normalized record.
4. Exports everything to a multi-sheet Excel report (sheets: Invoices, Nomina, Pagos).
5. Auto-generates the output filename from the data, e.g.
   `{RFC}_{Emitidas|Recibidas|Mixed}_{YYYY_MM}.xlsx`, and offers to open it.

Mexican context: CFDIs are downloaded from the SAT (today I download them
manually / massively from the SAT portal). The app's value is turning that pile
of XML into clean, accountant-ready Excel grouped by *Emitidas* (issued) vs
*Recibidas* (received).

## Current architecture (KEEP THIS STRUCTURE)
Since F2 (see ROADMAP.md), this is an installable package (`pip install -e .`,
`pyproject.toml`, `src/` layout), not flat root-level scripts:

- `src/cfdi_app/core.py` — UI-agnostic pipeline (single source of truth for the
  flow): `process_path()` walks a folder, `parse_xml_file_by_version()`
  dispatches per version, `process_zip_file()` handles .zip,
  `determine_file_naming_components()` / `build_default_filename()` build the
  dynamic name, `export_report()` writes Excel. Optional `on_log`/`on_progress`
  callbacks; NO Tkinter/Qt/print here. `ProcessResult.errors` lists per-file
  failures with a reason (not just a count).
- `src/cfdi_app/ui/` — **PySide6 GUI (primary entry: `python -m cfdi_app` /
  `run_gui.bat`)**: `state.py` (Qt-free state machine enum), `worker.py`
  (QThread worker), `main_window.py` (the window). Wraps `core` with a folder
  picker, progress bar, live log, explicit "Guardar Excel…"/"Abrir archivo"
  buttons. Processing runs in a `QThread` worker so the window stays responsive.
  **Golden rule:** dialogs only open from a direct user click, never from a
  worker/thread callback (see ROADMAP.md Bug 1).
- `src/cfdi_app/cli.py` — no-dialog console front-end (`python -m cfdi_app.cli`).
  The Tkinter `main.py` fallback was retired in F2 (ROADMAP.md decision D7).
- `src/cfdi_app/paths.py` — single owner of data directory paths (Documents/CFDI-Processor/).
- `src/cfdi_app/log_setup.py` — rotating file log + global exception hook.
- `src/cfdi_app/constants.py` — single source of truth for: XML namespaces per
  version, SAT catalogs (TipoDeComprobante, FormaPago, MetodoPago, UsoCFDI,
  RegimenFiscal), column orders (INVOICE_COLUMN_ORDER, PAGOS_COLUMN_ORDER),
  Nomina field maps, fuel-code helpers.
- `src/cfdi_app/parsers/xml_parser_33.py` — parses CFDI **3.3** → dict.
- `src/cfdi_app/parsers/xml_parser_40.py` — parses CFDI **4.0** → dict (Invoice or Nomina).
- `src/cfdi_app/parsers/pagos_parser_20.py` — parses **Pagos 2.0** complement → list of dicts.
- `src/cfdi_app/exporters/excel_exporter.py` — writes the DataFrames to Excel,
  one sheet per doc type, with column auto-sizing (single shared helper, not
  triplicated). Propagates exceptions (e.g. PermissionError if the destination
  is open in Excel) instead of swallowing them.

### CRITICAL DESIGN RULE — version isolation
Each CFDI version has its OWN parser module, in `src/cfdi_app/parsers/`.
Detection happens in `core.py` by reading the `Version` attribute and
`TipoDeComprobante`. When the SAT releases a new version (4.1, 5.0, a new
Pagos/Nómina complement, etc.), I add a NEW parser module and ONE dispatch
branch — existing parsers must NOT be touched. Never merge the version parsers
into one file. This isolation is intentional and must be preserved in every
change you propose. (It's also what lets the future Lite/Pro/Top editions
share one codebase — see ROADMAP.md §5.2.)

### Detection logic (current)
- `TipoDeComprobante == 'P'` and `Version == '4.0'` → Pagos 2.0 parser (returns a list).
- `Version == '3.3'` → 3.3 parser.
- `Version == '4.0'` → 4.0 parser (Invoice or Nomina by content).
- Each record carries a `CFDI_Type` field: `"Invoice"`, `"Nomina"`, or `"Pago"`,
  used to route it to the right Excel sheet.

### Supported complements
Nómina 1.2, Impuestos Locales (implocal), IEDU (educational institutions).

## Tech stack
- Python 3.11+
- Parsing: `xml.etree.ElementTree` (stdlib). (Open to `lxml` later for scale.)
- Excel: `pandas` + `openpyxl`.
- Current UI: Tkinter dialogs only (this is a stopgap, not a real GUI).

## SECURITY / LEGAL RULE — e.firma (FIEL) isolation  ⚠️
The user's FIEL/e.firma certificates (`.cer`, `.key`) and CIEC passwords are
legally sensitive credentials. They MUST be:
- Stored in an isolated, dedicated module/layer — never mixed into parsing or UI code.
- Encrypted at rest; never written to logs, temp files, or reports.
- Transmitted ONLY to official SAT endpoints over verified HTTPS.
- Handled with explicit, recorded user consent before any use.
This isolation is to protect users and to avoid legal liability. Treat it as a
hard architectural boundary, like the version-parser isolation.

## Known issues to fix later (do NOT fix unless asked)
- No persistence (re-parses every run) — resolved by the SQLite bóveda (ROADMAP.md F4).
- Test coverage gap: `tests/` only has CFDI 4.0 fixtures (Invoice + Nómina).
  No 3.3 or Pagos 2.0 fixtures yet → those parsers are untested. Add anonymized
  sample XMLs when available.
- ~~Hard-coded relative base path~~ — fixed in F2 (`paths.py`, Documents/CFDI-Processor/).
- ~~`excel_exporter.py` autosize loop triplicated~~ — fixed in F2 (shared `autosize_columns()` helper).

## Planned: working directory & auto-organization (FUTURE — not in Step 0)
Like other admin apps, the app will have a configurable **working directory**
(default chosen by the app, user can change it, but the internal structure is
always preserved):

```
%App_main_folder%/
├── BovedaCFDI/
│   └── {RFC}/                 # created on demand if the XML's RFC has no folder
│       └── {Emitidas|Recibidas}/   # by document direction
│           └── {YYYY}/        # stamped (timbrado) year, 4 digits
│               └── {MM}/      # stamped month, 01–12
└── Reports/
```

On import, the app checks whether the XML's RFC folder exists (creates it if
not), then files the XML under Emitidas/Recibidas → year → month based on the
**fecha de timbrado**. Belongs with Step 2 (the SQLite bóveda / organization
layer), not Step 0 or the first GUI.

## Roadmap
Full phase list (F0–F11), dependencies, and the current phase marker now live
in **ROADMAP.md §5** — that table supersedes any step list here. Quick recap of
where things stand: F0 (hygiene), F1 (GUI wrapper), F2 (stabilization), F2.5
(results viewer) **all CLOSED and owner-confirmed on real Windows**. F4's
technical design is DONE (ROADMAP.md §14: hybrid relational+JSON elastic
SQLite; MongoDB ruled out). **F2.6 (missing-field capture wave) BUILT
2026-07-04** (ROADMAP.md §15) — pending owner confirmation on real machine.
Along the way found and fixed a real structural bug in the Pagos 2.0 parser
(container-level fields being nulled by the per-Pago merge loop — see D27),
beyond the 2 bugs the original audit flagged. Per-concepto capture
(`ConceptosDetalle` + Nómina `*Detalle`) now lives in-memory per the §14.5
contract, ready for F4 to persist without re-parsing XML. Next up: F3
(working directory + auto-organization) or F4 (build the vault, already
designed) — to be decided with the owner. Safety tag `v0.2.5-estable` marks
the last known-good state before this wave of parser changes.

Long-term goal: package and sell it (Windows first; users are on Windows), as
**Lite/Pro/Top editions sharing one codebase** (ROADMAP.md §5.2, decision D10).

## How to work with me
- Build piece by piece, small steps, each one runnable.
- Always respect the version-isolation rule AND the e.firma isolation rule above.
- Don't over-engineer (no multi-OS/FreeBSD targeting now; Windows-first).
- When you change parsing, tell me which version module it touches.
