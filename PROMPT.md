# CFDI Processor — App Specification & Build Prompt

> Reusable spec. Paste into any AI (Claude, GLM, ChatGPT, Gemini) so it
> understands the app without seeing the code or screenshots. Keep it updated as
> the app evolves.

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
- `main.py` — orchestrator. Tkinter file dialogs (folder picker + save-as),
  `os.walk` over the directory, version dispatch, .zip extraction to a temp dir,
  dynamic filename logic, post-run "open file" prompt.
- `constants.py` — single source of truth for: XML namespaces per version, SAT
  catalogs (TipoDeComprobante, FormaPago, MetodoPago, UsoCFDI, RegimenFiscal),
  column orders (INVOICE_COLUMN_ORDER, PAGOS_COLUMN_ORDER), Nomina field maps,
  fuel-code helpers.
- `xml_parser_33.py` — parses CFDI **3.3** → dict.
- `xml_parser_40.py` — parses CFDI **4.0** → dict (Invoice or Nomina).
- `pagos_parser_20.py` — parses **Pagos 2.0** complement → list of dicts.
- `excel_exporter.py` — writes the DataFrames to Excel, one sheet per doc type,
  with column auto-sizing.

### CRITICAL DESIGN RULE — version isolation
Each CFDI version has its OWN parser module. Detection happens in `main.py` by
reading the `Version` attribute and `TipoDeComprobante`. When the SAT releases a
new version (4.1, 5.0, a new Pagos/Nómina complement, etc.), I add a NEW parser
module and ONE dispatch branch — existing parsers must NOT be touched. Never
merge the version parsers into one file. This isolation is intentional and must
be preserved in every change you propose.

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
- Hard-coded relative base path (`../../AdminXML`) — will become a user-chosen /
  default directory once the GUI exists. See "Planned: working directory &
  auto-organization" below.
- `excel_exporter.py` repeats the column-autosize loop 3× — candidate for a helper.
- No persistence (re-parses every run).
- Test coverage gap: `tests/` only has CFDI 4.0 fixtures (Invoice + Nómina).
  No 3.3 or Pagos 2.0 fixtures yet → those parsers are untested. Add anonymized
  sample XMLs when available.

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

## Roadmap (realistic, incremental — ship value each step)
0. Project hygiene: requirements file, clean layout, basic tests on the parsers.
   ✅ DONE — `requirements.txt`, `.gitignore`, `tests/test_parsers.py`
   (stdlib unittest; run `python -m unittest discover -s tests`).
1. Real GUI wrapping the EXISTING folder→parse→Excel flow — no new features,
   just make it an app. **Framework decided: PySide6** (official Qt for Python,
   LGPLv3 → free to use in a closed-source/paid app; cross-platform Windows/
   Linux/macOS). NOT PyQt6 (GPL/commercial → would require paying or
   open-sourcing the whole app).
2. SQLite "bóveda": parse once, store metadata, stop re-scanning; enables search
   and dedup.
3. Reports & filters on top of the DB (by RFC, month, type, Emitidas/Recibidas).
4. SAT download (isolated spike). SAT mass download supports CIEC login and
   FIEL/e.firma; the FIEL path is a signed SOAP web-service flow with async
   request→wait→verify→download. Lean on existing Python libraries for the
   crypto/SOAP handshake rather than reinventing it. (Requires the e.firma
   isolation layer above.)
5. **Validación de estatus** — query SAT for each CFDI's status
   (vigente / cancelado / no encontrado), like Contpaqi and MiAdminXML do.
   Cache results. Can go live once SAT connectivity (step 4) exists.
6. **Módulo de Cancelación** — cancel CFDIs through the SAT (with motivo de
   cancelación, folio sustituto where required, and acuse retrieval). Requires
   FIEL. High legal/financial sensitivity — build carefully, with confirmations
   and audit logging. Goes live after SAT connectivity and validation.
7. Much later / optional: PDF generation, EFOS / lista negra checks, Nómina
   analytics, and eventually a Contabilidad Electrónica module (catálogo de
   cuentas, balanza, DIOT) as a low-cost alternative to expensive licenses
   (Contpaqi, MiAdminXML).

Long-term goal: package and sell it (Windows first; users are on Windows).

## How to work with me
- Build piece by piece, small steps, each one runnable.
- Always respect the version-isolation rule AND the e.firma isolation rule above.
- Don't over-engineer (no multi-OS/FreeBSD targeting now; Windows-first).
- When you change parsing, tell me which version module it touches.
