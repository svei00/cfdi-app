# Design Doc — Combustible false-positive fix + UX improvements (2026-07-09)

Status: DESIGN APPROVED by owner (Svei), pending build session with Opus/Sonnet.
Rule: this doc contains NO code — architectural decisions only. Implementation
must follow ROADMAP governance (D11: never remove working functionality without
asking; D20: git tag before touching parsers or parser-adjacent constants).

---

## Task A — Combustible false positive (BUG, confirmed with real XML)

**Evidence file:** `C:\AdminXML\BovedaCFDI\GOOH841231EPA\Recibidas\2026\06\2b1b6d12-3f8c-4198-a102-7b8c24a2b09f.xml`
(steel/hardware invoice, wrongly flagged as Combustible)

| Concepto | ClaveProdServ | ClaveUnidad | Descripcion |
|---|---|---|---|
| 1 | 30102304 (steel bars) | KGM | SOLERA 1/4 X 1 1/2 |
| 2 | 30102304 | KGM | SOLERA 3/16 X 1 |
| 3 | 78121601 (freight load/unload service) | E48 | CARGAS Y DESCARGAS-1TON |

**Root cause (confirmed, not hypothesis):** concepto 3 fired the text-heuristic
fallback in `src\cfdi_app\parsers\xml_parser_40.py` (~line 624):

1. `E48` is listed in `FUEL_UNITS` (`constants.py` ~line 583), but E48 =
   "Unidad de servicio" — the generic unit used by every service provider
   (Telmex, CFE, insurers, freight). It is not fuel-specific.
2. The keyword check is a Python **substring** test: `"GAS" in description`.
   "CAR**GAS**" and "DESCAR**GAS**" both contain G-A-S, so a freight service
   matched the fuel keyword. Same failure class: "GASTOS", "ENGASTE", etc.

**Fix (conceptual — build session implements):**

1. Keyword matching must be **whole-word**, not substring. "GAS" matches
   "GAS", "GAS LP", "GAS NATURAL"; never "CARGAS"/"DESCARGAS"/"GASTOS".
   This alone kills the observed false positive.
2. Demote **E48**: remove it from `FUEL_UNITS`, or require a fuel-unambiguous
   keyword (MAGNA / PREMIUM / DIESEL / GASOLINA) when unit is E48; reserve the
   looser GAS / COMBUSTIBLE keywords for volumetric units (LTR, GAL, etc.).
3. Keep the heuristic itself — it is the documented fallback (D19–D22:
   combustible = inferencia) for emisores that don't use 1510-family claves.
4. Constants are shared: the fix applies to both parsers (4.0 and 3.3) via
   `constants.py`. Tag before the change (D20). Add a regression test using
   the "CARGAS Y DESCARGAS" + E48 pattern.

---

## Task B1 — Tooltips on truncated cells

**Decision: model-level, `Qt.ToolTipRole` in `data()` of the source model**
(`results_model.py`), not view-level event handling.

- QSortFilterProxyModel forwards roles transparently → works through
  sort/filter with zero extra wiring; per-cell for free.
- Every cell returns its full untruncated value as tooltip. Optional polish:
  suppress tooltip when it equals the visible text.
- **Conceptos column:** tooltip renders one concept per line (parsers keep
  `ConceptosDetalle` as list-of-dicts since F2.6 / D25, so structured data is
  already available), instead of the flattened cell string. This is the core
  requirement: read one concept without expanding anything.
- Edge cases to handle: escape `<`, `>`, `&` (or force plain-text tooltips) —
  supplier descriptions can contain angle brackets and Qt interprets rich
  text; cap very long concept lists (~30 lines + "… y N más").

---

## Task B2 — Serie/Folio: merged vs. split

**Decision: BOTH.** Keep "Factura" (merged `Serie-Folio`) always present, add
"Serie" and "Folio" as separate columns **hidden by default**, exposed via the
already-committed configurable column selector (D18). No runtime merge/split
toggle button — the if-block lives in column-visibility defaults, not parse
logic.

- Rationale: commercial users (accounting firms) need Serie and Folio as
  separate VLOOKUP/INDEX-MATCH keys against ERP exports; splitting "A-123" in
  Excel is ambiguous when Serie itself contains a hyphen.
- Removing "Factura" would break the owner's INDEX/MATCH sheets and violate
  D11 → it stays, never moves.
- Parser impact: emit three fields (Serie, Folio, Factura) instead of one.
  Purely additive; existing Factura logic (serie-folio / folio-only / None)
  stays byte-identical. Parser wave → tag first (D20).
- Excel export: new columns join `INVOICE_COLUMN_ORDER` adjacent to "Factura".

---

## Task B3 — Navigation redesign (vault browser)

**Decision: left sidebar panel (dockable/collapsible) mirroring the vault
hierarchy**, replacing the folder picker as PRIMARY flow. "Open folder…" stays
as secondary menu action for ad-hoc XMLs outside the vault (D11).

Flow (owner-confirmed 2026-07-09):

1. **RFC selector** — lists subfolders of the vault root. Multi-RFC support
   means *fast client switching* (pick RFC A → work → pick RFC B), **NEVER
   mixing/comparing two RFCs in one table/report. Hard rule.**
2. Click RFC → shows **Emitidas / Recibidas** (mirrors the folder). Pick one
   (both checkable is acceptable within same RFC; Tipo column distinguishes).
3. Click Emitidas/Recibidas → shows available **years**. Each year node has a
   **checkbox = select the whole year** (all its months).
4. Click year → shows available **months**, each with checkbox → one or
   several months (bimonthly, quarterly, semester use cases).
5. **Comparing periods (years or months) of the SAME RFC is allowed** and the
   tree/checkbox model supports it natively.
6. Preset shortcut buttons: Bimestre 1–6, Trimestre 1–4, Semestre 1–2, Año
   completo — they just check the corresponding month boxes.
7. "Cargar" gathers checked (RFC, tipo, año, mes) paths → feeds the EXISTING
   processing pipeline unchanged. Architecturally this is a file-list builder
   in front of the current engine — low risk.
8. Selection state (last RFC, etc.) persists in `settings.json`.
9. F5 note: pre-F5 this enumerates folders; when SQLite lands, the same
   sidebar reads year/month availability from the DB. No UI change.

**CONSTRUIDO 2026-07-12 (decisiones del dueño al arrancar B3):**

- **Modelo de estado = "un árbol grande"** (el dueño eligió esta opción sobre
  el context-switch estructural): TODOS los RFCs de la bóveda se muestran a la
  vez, con casilla en cada nivel (RFC/Emitidas·Recibidas/año/mes). La regla
  dura de un solo RFC se hace cumplir **en la capa de datos**
  (`vault.build_load_folders` lanza `MultipleRfcError`) y se **confirma** al
  usuario con un aviso al pulsar "Cargar" (señal `single_rfc_violation` → la
  ventana muestra el `QMessageBox`; nace de un clic directo, no rompe la regla
  anti-Bug-1). Comparar periodos del mismo RFC: nativo.
- **Capa de acceso aislada** en `cfdi_app/vault.py` (`VaultSource` +
  `FolderVaultSource`), costura para F4: la barra lateral no conoce os.walk ni
  SQLite. `core.process_paths()` (nuevo) alimenta el motor existente sin
  tocarlo; `process_path()` intacto.
- **Descargar** = botón gris + menú deshabilitado (placeholder F6). El flujo
  real de descarga+auto-categorización y la vista "Reports/árbol global" se
  entregan a **Fable** (ver ROADMAP.md §10.6).
- **Iconografía** pendiente (ROADMAP.md §10.5); la UI de B3 es solo texto.
- "Abrir carpeta…" ad-hoc movido a **menú Archivo** (secundario, D11 intacto).

---

## Task C — Copy from results table (priority: MUST)

**Confirmed absent today:** zero clipboard code in the repo; plain QTableView
provides no Ctrl+C.

**Decision:** copy any selected cell(s) to the SYSTEM clipboard as plain text
so it pastes anywhere (Excel, Word, web, WhatsApp — owner's explicit scope).

- Single cell → just the value (RFC, UUID, Concepto…), no trailing junk.
  Owner's driving use case: copy an RFC/UUID out of a cell instead of retyping.
- Multi-cell/row selection → tab-separated columns + newline-separated rows
  (Excel splits into cells natively).
- Copy **displayed/formatted** values (what you see is what you paste), in
  visual order as shown (respecting active sort/filter).
- Bindings: standard copy shortcut + right-click context menu "Copiar" on the
  cell. User-initiated → no conflict with the anti-Bug-1 modal rule.

---

## Suggested build order

1. Task C (copy) — smallest, immediate daily value.
2. Task B1 (tooltips) — small, model-only.
3. Task A (combustible rule) — constants + tests, tag first (D20).
4. Task B2 (Serie/Folio) — parser wave, tag first (D20).
5. Task B3 (vault navigation) — largest; its own phase.
