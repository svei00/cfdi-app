# Diseño B3-R2 — Carátula, módulo Administrador de Bóveda y correcciones del árbol

> Fecha: 2026-07-13
> Origen: primera prueba real del dueño de la B3 construida (2026-07-12), con
> capturas comparativas contra MiAdminXML. Feedback levantado en sesión con
> Fable; decisiones confirmadas por el dueño una por una.
> Constructor: Sonnet 5 (u Opus 4.8). Fable NO escribe código — este documento
> es la especificación completa y autocontenida.
> Materializa ROADMAP.md §5.3 (evolución a shell/dashboard) — el dueño la
> des-difirió explícitamente en esta ronda.

---

## Resumen de fallas reportadas (prueba real 2026-07-13)

| # | Falla | Causa en código | Decisión que la corrige |
|---|-------|-----------------|-------------------------|
| 1 | La tabla de resultados es omnipresente; "exceso de negro"; el dueño pidió carátula desde los requisitos originales | La ventana única de F2/F2.5 nunca evolucionó a shell (§5.3 diferida) | D36 |
| 2 | Marcar el RFC marca Emitidas+Recibidas; marcar tipo marca todos los años; marcar año marca todos los meses | Cascada padre→hijos en `vault_sidebar._set_children_state` | D37 |
| 3 | Carpetas basura ("Here", "Master") aparecen como RFCs | `FolderVaultSource` lista cualquier subcarpeta | D37 |
| 4 | Los presets no son toggle: segundo clic en "Trimestre 3" NO desmarca julio-septiembre | `_apply_preset` solo hace `setCheckState(Checked)` | D38 |
| 5 | Estado marcado de presets invisible en tema oscuro; sin atajos de teclado | Botones planos sin estado checkable ni stylesheet | D38 |
| 6 | Panel de bóveda cerrable y se pierde: "Recargar bóveda" no lo restaura; el toggle escondido en menú Ver es mal lugar | `QDockWidget` cerrable + `toggleViewAction` en Ver | D36 (el dock DESAPARECE) |
| 7 | La app ignora la redirección de Documents de Windows (el Documents del dueño no está en C:) | `paths._documents_dir()` usa `expanduser("~")\Documents` a ciegas | D39 |
| 8 | No se puede cambiar la ubicación de la bóveda (requisito primigenio) | No construido (F3) | D39 (se adelanta) |

---

## Decisiones registradas (continuar numeración en ROADMAP.md §7 al cerrar)

| # | Decisión | Fecha | Por qué |
|---|----------|-------|---------|
| D36 | **Shell de una sola ventana con páginas apiladas (`QStackedWidget`)**: página **Inicio (carátula)** + página **módulo "Administrador de Bóveda"**. NO ventanas independientes estilo MiAdminXML, NO MDI (`QMdiArea`). El módulo se abre desde botón de la carátula o desde el menú; "cerrarlo" = volver a Inicio; se reabre igual de fácil. La tabla de resultados, el árbol de bóveda, el log y los controles de proceso viven DENTRO del módulo. El `QDockWidget` se elimina por completo | 2026-07-13 | El dueño validó el patrón "módulo que abres/cierras desde menú" de MiAdminXML, pero las páginas apiladas lo SUPERAN (petición explícita: "que lo supere"): una ventana jamás se pierde (falla #6 imposible por construcción), sin gestión de ventanas para un contador no técnico, y sin el aire noventero de MDI. Materializa §5.3 |
| D37 | **Divulgación progresiva en el árbol: casillas SOLO en meses.** RFC, Emitidas/Recibidas y Año son navegación pura (clic expande/colapsa, sin checkbox). Todo arranca desmarcado; el usuario decide. `FolderVaultSource` filtra los nodos RFC por patrón de RFC válido (`[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}`, case-insensitive) — carpetas que no casan NO aparecen en el árbol | 2026-07-13 | Elección del dueño (opción "solo meses"): es el modelo mental de MiAdminXML (solo los meses tienen casilla) pero en árbol, que el dueño prefiere ("el árbol está bien y es menos molesto"). Elimina de raíz la cascada sorpresiva. El filtro RFC mata las carpetas basura ("Here", "Master") de la vista |
| D38 | **Presets se CONSERVAN como diferenciador** (no existen en MiAdminXML — valor agregado, y distancia anti-plagio). Tres correcciones: (a) **toggle real** — si todos los meses disponibles del preset ya están marcados, el clic los desmarca; si no, los marca; (b) **estado visual notorio** — botones `checkable` con stylesheet `:checked` usando `palette(highlight)`, sincronizados con el estado real de los meses (marcar/desmarcar meses a mano actualiza el botón); (c) **atajos de teclado**: `Ctrl+1..6` bimestres, `Ctrl+Shift+1..4` trimestres, `Ctrl+Alt+1..2` semestres, `Ctrl+0` año completo, `F5` recargar bóveda | 2026-07-13 | "Atajo de periodo" implica atajo de teclado (dueño). El no-toggle fue calificado de "GRAN FALLA de GUI". El dueño confirmó conservar los presets aunque MiAdminXML no los tenga |
| D39 | **Ruta de la bóveda configurable con mudanza TOTAL.** (a) El Documents por defecto se resuelve vía API de Windows (`SHGetKnownFolderPath(FOLDERID_Documents)` por ctypes; fallback a `expanduser` si falla o no es Windows) — respeta carpetas redirigidas. (b) Nueva clave `vault_root` en `settings.json` (extiende el mecanismo D14; NUNCA un segundo mecanismo). (c) Acción de menú **"Cambiar ubicación de bóveda…"**: elige carpeta destino y **MUEVE la bóveda COMPLETA** (la carpeta BovedaCFDI con todos sus RFCs/tipos/años/meses) — jamás mudanzas por-RFC. El default se mantiene `Documents\CFDI-Processor\BovedaCFDI` (D4 intacta) | 2026-07-13 | Requisito primigenio del dueño que nunca se construyó. Su Documents está redirigido fuera de C: — el `expanduser` ciego es un bug real, no preferencia. "Si movemos algo de ubicación solo se mueve la bóveda y TODO lo que tiene dentro" (dueño, textual) |
| D40 | **Regla anti-plagio de UI.** Términos genéricos del dominio SAT (bóveda, CFDI, emitidas/recibidas, año/mes) se usan sin miedo — nadie los posee. PROHIBIDO clonar de MiAdminXML: acomodo visual, iconografía, textos literales de sus menús y nombres propios de sus módulos ("Administración de XML 4.0"). Nuestro módulo se llama **"Administrador de Bóveda"**; el objetivo no es imitar sino superar en intuitividad. El menú **Ver se elimina** (versión/licencia irán en un futuro menú Ayuda, donde los usuarios lo esperan) | 2026-07-13 | Preocupación explícita del dueño ("no quiero que me acusen de plagio"). Codebase ya es distinta (Python/PySide6 vs .NET); esta regla protege la capa visual |

---

## Especificación de construcción

### 1. Shell: `MainWindow` reorganizada (D36)

- El central widget pasa a ser un `QStackedWidget` con dos páginas:
  - **Página 0 — Carátula (`InicioPage`)**, nueva clase en `ui/inicio_page.py`.
  - **Página 1 — Módulo (`AdminBovedaPage`)**, nueva clase en
    `ui/admin_boveda_page.py`, que absorbe TODO lo que hoy está en el central
    widget + el dock: árbol de bóveda (izquierda, dentro de un `QSplitter`
    horizontal), y a la derecha: etiqueta de origen, botones de acción,
    barra de progreso, visor de resultados, log.
- `QDockWidget`, `_build_sidebar()` y el `toggleViewAction` de Ver se eliminan.
  El `VaultSidebar` (corregido, §3) se instancia DENTRO de `AdminBovedaPage`.
- Navegación:
  - Carátula → módulo: botón grande "Administrador de Bóveda" o menú
    `Bóveda → Administrador de Bóveda` (atajo `Ctrl+B`).
  - Módulo → carátula: botón "⌂ Inicio" en la esquina superior izquierda del
    módulo (y la misma acción de menú funciona como toggle de página).
  - Si hay procesamiento corriendo, cambiar de página NO lo cancela (los
    hilos y señales viven en `MainWindow`, no en la página; el estado
    PROCESSING sigue las reglas de `ui/state.py` sin cambios).
  - "Abrir carpeta de XMLs sueltos…" (flujo ad-hoc, D11) también navega al
    módulo: el módulo es EL espacio de trabajo de procesamiento, venga la
    carga de bóveda o de carpeta suelta.
- La máquina de estados (`AppState`, `widget_states_for`) NO cambia. Las
  reglas anti-Bug-1 (ningún diálogo desde slots de worker) NO cambian.

### 2. Carátula (`InicioPage`)

Composición vertical, centrada, generosa en espacio (matar el "exceso de
negro" con contenido, no con más tabla):

1. Título de la app + subtítulo corto.
2. **Zona de banner** (D36 + petición del dueño):
   - `QLabel` clicable (cursor de mano) que abre `https://excelsolutionsv.com`
     con `QDesktopServices.openUrl` — clic directo del usuario, sin diálogos.
   - Si existe `assets/banner.gif` (o `.png`), se muestra con `QMovie`/pixmap
     escalado; si NO existe, placeholder de texto estilizado
     ("Excel Solutions — soluciones contables") para que la zona quede lista
     sin bloquear esta fase. NO empaquetar publicidad de terceros hoy.
3. **Botones de módulo** (fila u columna de botones grandes, solo texto por
   ahora — la iconografía sigue pendiente en ROADMAP §10.5):
   - "Administrador de Bóveda" — activo, navega a página 1.
   - "Descargar del SAT" — deshabilitado (F6, CIEC/e.firma), tooltip explicativo.
   - "Reportes" — deshabilitado, tooltip "próximamente" (diseño en curso con
     Fable, ver docs/prompt-fable-descarga-sat-reports.md).

### 3. Árbol de bóveda corregido (D37)

En `vault_sidebar.py`:

- `_make_item`: solo los items de tipo `"month"` reciben
  `setCheckable(True)`; RFC/tipo/año se crean sin casilla.
- Eliminar `_set_children_state` y `_refresh_ancestors` (ya no hay cascada ni
  tri-estado). `_on_item_changed` queda solo para sincronizar el estado visual
  de los botones de preset (§4).
- `gather_selections()` no cambia de contrato: sigue devolviendo hojas
  marcadas (meses). La regla dura de un solo RFC sigue viviendo en
  `vault.build_load_folders` (sin cambios).
- Clic en un nodo de navegación expande/colapsa (conectar `clicked` del
  QTreeView a un slot que haga toggle de expansión, además de la flecha).
- En `vault.py`, `FolderVaultSource.rfcs()` filtra con el patrón RFC de D37.
  El filtro vive en la CAPA DE DATOS (vault.py), no en el widget — así F4
  (SQLite) hereda el mismo contrato.

### 4. Presets corregidos (D38)

- Botones `setCheckable(True)` con stylesheet:
  `QPushButton:checked { background-color: palette(highlight); color: palette(highlighted-text); font-weight: bold; }`
- Semántica toggle sobre el año seleccionado:
  - Estado del botón = "TODOS los meses disponibles de ese preset están
    marcados" (se recalcula cuando cambia cualquier casilla de mes y cuando
    cambia la selección de año).
  - Clic con todos marcados → desmarcarlos. Clic en cualquier otro caso →
    marcarlos. Preset sin meses disponibles en ese año → mensaje de estado
    (comportamiento actual se conserva).
- Atajos (`QShortcut` a nivel del módulo, activos solo cuando la página del
  módulo está visible): `Ctrl+1..6` bimestres, `Ctrl+Shift+1..4` trimestres,
  `Ctrl+Alt+1..2` semestres, `Ctrl+0` año completo, `F5` recargar bóveda,
  `Ctrl+B` ir al Administrador de Bóveda (global de ventana).

### 5. Ruta de bóveda (D39)

En `paths.py`:

- `_documents_dir()` pasa a intentar primero
  `SHGetKnownFolderPath(FOLDERID_Documents)` vía `ctypes` (solo Windows),
  con fallback al comportamiento actual. Función pequeña, comentada estilo
  profesor (regla de estilo del dueño).
- `paths.py` conserva SOLO el cálculo del default. La fuente de verdad de la
  ruta ACTIVA es `settings.get_vault_root()`:
  - Nueva clave `"vault_root"` en `_DEFAULTS` (vacía = usar default de paths).
  - `get_vault_root()` devuelve la guardada si existe y es directorio válido;
    si no, el default. `set_vault_root(path)` la persiste.
  - OJO import circular: `settings` ya importa `paths`; `paths` NO debe
    importar `settings`. Quien necesita la ruta activa (main_window,
    FolderVaultSource) la pide a `settings`.
- Acción de menú `Bóveda → Cambiar ubicación de bóveda…` (clic directo →
  diálogos legítimos):
  1. `QFileDialog.getExistingDirectory` para elegir la carpeta PADRE destino.
  2. Validaciones (rechazar con mensaje claro): destino dentro de la bóveda
     actual; destino ya contiene una carpeta `BovedaCFDI` no vacía; destino
     sin permisos de escritura; estado PROCESSING activo (deshabilitar la
     acción durante procesamiento, igual que `set_busy`).
  3. Confirmación explícita (`QMessageBox.question` — nace del clic, legal):
     "Se moverá TODA la bóveda (N RFCs) de X a Y".
  4. La mudanza corre en un worker QThread (patrón canónico §6.3, como
     `ProcessWorker`) — `shutil.move` puede tardar entre discos y NO debe
     congelar la GUI. Progreso por carpeta de RFC movida.
  5. Al terminar: `set_vault_root(nueva_ruta)`, recargar el árbol, mensaje en
     el log. Si falla a medias: reportar qué se movió y qué no, NO borrar
     nada del origen que no se haya copiado (mover = copiar+verificar+borrar
     solo en cruce de discos; en el mismo disco `os.rename` es atómico).
- La mudanza mueve **la carpeta BovedaCFDI completa**. Jamás por-RFC (dueño,
  textual).

### 6. Lo que NO se toca

- Parsers, constants, exporters, core.process_path/process_paths: CERO cambios.
- Regla dura un-solo-RFC (`vault.build_load_folders` + `MultipleRfcError`).
- Reglas anti-Bug-1 y máquina de estados.
- "Abrir carpeta de XMLs sueltos…" sobrevive en Archivo (D11).
- El visor de resultados (`ResultsView`) por dentro: solo se RE-UBICA al módulo.

### 7. Pruebas (regresión + nuevas)

- Actualizar `tests/test_vault_sidebar.py`: casillas solo en meses; sin
  cascada; toggle de presets (marcar/desmarcar); sincronía visual del botón;
  filtro de carpetas no-RFC.
- Nuevas en `tests/test_settings.py`: `vault_root` get/set/default/inválida.
- Nuevas `tests/test_vault_move.py`: mudanza feliz en tmp dirs; destino con
  bóveda no vacía → rechazo; destino dentro del origen → rechazo.
- Nueva prueba de navegación (offscreen): carátula ↔ módulo, botones de
  módulo deshabilitados correctos, banner placeholder presente.
- Suite completa verde (`python -m unittest discover -s tests`) antes de
  reportar. UI-only + settings: sin tag D20 (criterio de B1/C).

### 8. Construcción NO cubierta hoy (que Sonnet no invente alcance)

- Iconografía (ROADMAP §10.5) — botones de texto.
- Banner con contenido real/rotación — solo la zona y el placeholder.
- Descarga SAT y vista Reportes — placeholders grises (diseño con Fable en
  docs/prompt-fable-descarga-sat-reports.md).
- Selector de columnas visibles, export filtrado (F2.7), PT Pro (F2.8): no.
- Tema claro/oscuro completo (§5.4): no; solo el stylesheet puntual de D38.
