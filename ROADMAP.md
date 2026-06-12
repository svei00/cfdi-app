# ROADMAP.md — CFDI Processor: diagnóstico, fases y arquitectura

> **Documento maestro del proyecto.** Nació para construir la Fase 2
> (2026-07-01) y desde entonces es el registro vivo de fases, decisiones y
> arquitectura. Autocontenido: un modelo debe poder construir la fase siguiente
> leyendo SOLO este archivo más el código. Complementa a `PROMPT.md` (spec
> general del producto) y a `Roadmap_Aplicacion_CFDI.md` (visión estratégica de
> largo plazo).

---

## 0. Gobernanza de este documento (registrada 2026-07-04)

- ROADMAP.md es un documento **VIVO** y pertenece al **dueño del proyecto**,
  no a ningún modelo "director" en particular. Fable, Opus, Sonnet u otro
  pueden dirigir el diseño o la construcción en distintos momentos; el
  documento y sus decisiones no cambian de autoridad por ello.
- Cualquier decisión registrada (D1 en adelante) **puede revisarse** si su
  razón ya no aplica o si la visión del dueño cambió. Revertir una decisión
  con causa no es un error: es parte del proceso.
- Lo único innegociable es el **registro**: toda decisión nueva, modificada o
  revertida se anota en §7 con fecha y razón, para que quien construya después
  entienda el porqué sin re-derivarlo.

---

## 1. Estado al inicio del diseño de F2 (2026-07-01 — HISTÓRICO; el estado post-F2 está en §9)

- Entorno de desarrollo: Windows 11, Python 3.14, deps en `requirements.txt`
  (pandas, openpyxl, PySide6 6.11 — instalada y verificada). Pruebas con
  `unittest` de la stdlib (sin pytest, a propósito: cero fricción).
- Pipeline funcional: CFDI 3.3 / 4.0 / Nómina 1.2 / Pagos 2.0 → Excel multi-hoja.
- 9 pruebas verdes: `python -m unittest discover -s tests` (solo fixtures 4.0;
  3.3 y Pagos SIN cobertura — falta conseguir XMLs anonimizados).
- GUI PySide6 (`gui.py`) construida pero **rota en máquina real** (Bug 1 abajo).
- Front-ends actuales: `gui.py` (PySide6), `main.py` (Tkinter/consola, legacy),
  `cli.py` (sin diálogos, usado por `test.bat`).
- Módulos planos en la raíz del repo. Último commit relevante: `ff093e7`.

## 2. Reglas INTOCABLES (heredadas de PROMPT.md)

1. **Aislamiento por versión:** cada versión CFDI tiene SU módulo parser
   (`xml_parser_33.py`, `xml_parser_40.py`, `pagos_parser_20.py`). Nueva versión
   SAT = nuevo módulo + una rama de despacho. Jamás fusionar ni tocar los
   existentes. En F2 los parsers SOLO cambian de carpeta — ni una línea de lógica.
2. **Aislamiento e.firma/FIEL** (aplica desde F6): credenciales en capa dedicada,
   cifradas en reposo, nunca en logs/temporales/reportes, solo a endpoints
   oficiales SAT por HTTPS verificado, con consentimiento explícito del usuario.

## 3. Diagnóstico de los bugs reportados

### Bug 1 — GUI "congelada" al terminar el procesamiento

**Síntoma:** procesa, termina, y la app no responde: no pregunta nada, no
permite otra acción.

**Evidencia:** toda la cadena de hilos (worker → `on_worker_finished` →
`thread.quit()` → `on_thread_finished` → exportación) fue verificada funcionando
en esta misma máquina en modo offscreen con diálogos simulados. Lo primero que
difiere en una corrida real son los diálogos nativos.

**Causa raíz (confianza alta):** `gui.py` dispara una cadena de diálogos modales
AUTOMÁTICOS desde el callback de fin de hilo (`on_thread_finished` →
`_export_result` → `QFileDialog.getSaveFileName` en gui.py:240 →
`QMessageBox.question` en gui.py:257). Un diálogo nativo lanzado
programáticamente (no por clic) puede abrirse sin activación: detrás de la
ventana o sin foco. Un modal invisible bloquea toda la app = el síntoma exacto.
`_set_busy(True)` (gui.py:201) amplifica: los botones quedan deshabilitados
hasta que el diálogo invisible se cierre.

**Defectos contribuyentes (corregir todos en F2):**

| # | Defecto | Ubicación |
|---|---|---|
| 1 | Diálogos modales automáticos desde callback de hilo | gui.py:221-265 |
| 2 | `self.thread` sombrea el método heredado `QObject.thread()` | gui.py:158 |
| 3 | `worker.deleteLater()` posteado a un hilo ya muerto (nunca se procesa; fuga) | gui.py:195-196 |
| 4 | `excel_exporter.py` traga TODAS las excepciones (`except Exception: print`) → si el .xlsx destino está abierto en Excel, falla en silencio y la GUI reporta éxito falso | excel_exporter.py:155-157 |
| 5 | Cero logging a archivo → imposible diagnosticar en máquina real | todo el proyecto |

**Solución diseñada:** ver §6 (máquina de estados + patrón de hilos canónico +
logging). La corrección de fondo: **ningún diálogo se abre solo; los diálogos
nacen de clics del usuario**, lo que garantiza foco y elimina la clase entera
del bug.

### Bug 2 — `run_gui.bat` deja una terminal negra abierta

**Causa raíz:** `run_gui.bat` ejecuta `python gui.py`. `python.exe` es el
intérprete DE CONSOLA: mantiene la ventana cmd atada durante toda la vida de la
app (negra porque la GUI no imprime nada), y el .bat espera a que termine.

**Solución diseñada:**
- `run_gui.bat` → `start "" pythonw -m cfdi_app` (`pythonw.exe` no crea consola;
  `start` desacopla y el cmd se cierra al instante).
- `run_gui_debug.bat` → `python -m cfdi_app` (consola visible, para diagnóstico).
- **Caveat crítico:** `pythonw` descarta stdout/stderr → un crash de arranque es
  invisible. Por eso el logging a archivo + `sys.excepthook` (§6) son
  PREREQUISITO de este cambio, no opcionales.
- Definitivo para distribución: PyInstaller `--windowed` (Fase F9, sin prisa).

## 4. Deuda técnica y riesgos identificados

1. **Privacidad ⚠️:** git rastrea 7 reportes `.xlsx` en
   `CFDI_Processor_App/Reports/` con RFCs aparentemente reales (p.ej.
   `GOOH841231EPA`) y 23 `.pyc` viejos. `.gitignore` no des-rastrea lo ya
   commiteado. Acción F2: `git rm --cached` de ambos grupos. (El historial los
   conserva; si el repo se comparte algún día, evaluar `git filter-repo`.)
2. **`BASE_APP_DIR` resuelve a `D:\AdminXML`** — raíz del disco, calculado desde
   la ubicación del repo, y hereda el nombre de la app competidora (MiAdminXML).
   Acción F2: mover default a `Documents\CFDI-Processor\` (§6, decisión D4).
3. Errores por archivo se pierden: `core.parse_xml_file_by_version` devuelve
   `None` sin registrar cuál archivo falló ni por qué (core.py:91-95). Para
   contadores, "3 errores" sin lista de archivos es inaceptable.
4. `excel_exporter.py`: bucle de auto-ancho triplicado + `print()` en vez de
   logging + el `except` tragón del Bug 1.4.
5. README.md desactualizado (describe la era pre-GUI).
6. Sin fixtures 3.3 / Pagos 2.0 en `tests/` (parsers sin red de seguridad).
7. Escalabilidad: todo en memoria + re-parseo total por corrida (lo resuelve F4
   bóveda SQLite, ya planeada); auto-ancho O(celdas) será cuello de botella con
   decenas de miles de filas (aceptable hasta F5).

## 5. Fases del proyecto (completas)

| Fase | Nombre | Entrega | Depende de | Estado |
|---|---|---|---|---|
| F0 | Higiene | requirements, .gitignore, 9 pruebas | — | ✅ Hecha |
| F1 | GUI envolvente | GUI PySide6 sobre carpeta→parseo→Excel | F0 | ⚠️ Construida, rota (Bugs 1/2) |
| F2 | Estabilización y reestructura | GUI estable + logging + paquete + datos en Documents + limpieza git | F1 | ✅ **CERRADA** — construida 2026-07-03, confirmada por el dueño en máquina real 2026-07-04 (ver §9) |
| F2.5 | Visor de resultados en la GUI | Tabla del lote procesado con pestañas espejo del Excel (Invoices/Nómina/Pagos) + fila de TOTALES (subtotal, descuento, IVA, total) + botón "Abrir carpeta" + `settings.json` mínimo que recuerda la última carpeta de guardado (D14) + filtro incremental (D15). **Restricción dura D13: Qt Model/View — `QTableView` + `QAbstractTableModel`; `QTableWidget` PROHIBIDO.** Sin SQLite. Definición completa en §11 | F2 | ✅ Construida 2026-07-04 (ver §12) — **falta confirmación del dueño en máquina real** |
| F3 | Directorio de trabajo + auto-organización | Settings persistentes (EXTIENDE el `settings.json` sembrado en F2.5, no crea otro mecanismo), checkbox "usar siempre la misma ruta de guardado" (D14), **selector de columnas visibles del visor** (checkboxes, persistido — D18), selector de working dir, archivado `BovedaCFDI\{RFC}\{Emitidas|Recibidas}\{YYYY}\{MM}` (año/mes = fecha de timbrado) | F2.5 | Pendiente |
| F4 | Bóveda SQLite | Parseo único, metadatos en DB, dedup por UUID, búsqueda | F2 | Pendiente |
| F5 | Reportes y filtros | Tablas Qt Model/View, filtros RFC/mes/tipo + **búsqueda de texto FTS5** (nativa de SQLite, cero dependencias) sobre descripciones de conceptos | F4 | Pendiente |
| F6 | SAT — descarga | CIEC primero, FIEL después; capa aislada e.firma | F2 (guarda en F4) | Pendiente |
| F7 | Validación de estatus | Vigente/cancelado/no encontrado + caché | F6+F4 | Pendiente |
| F8 | Cancelación | Motivo, folio sustituto, acuse, confirmaciones + bitácora | F6, F7 | Pendiente |
| F9 | Empaque, ediciones y licencias | PyInstaller --windowed + instalador + **ediciones Lite/Pro/Top con matriz de features y licencia** (ver §5.2). Disparador: primer usuario externo | F2+ | Sin prisa (solo el dueño usa la app hoy) |
| F10 | Módulos avanzados | PDF, EFOS, analítica nómina, Contabilidad Electrónica/DIOT | F4–F7 | Largo plazo |
| F11 | Búsqueda semántica (OPCIONAL) | Embeddings + `sqlite-vec` (Apache-2.0/MIT, libre) para búsqueda por significado sobre descripciones de conceptos. **Disparador:** que FTS5 (F5) se quede corto Y exista modelo de embeddings LOCAL pequeño y empaquetable | F4+F5 | Opcional, largo plazo |

### 5.1 Nota de diseño: estrategia de búsqueda (SQL vs FTS5 vs vectores)

Tres niveles, del más barato al más caro — implementar en este orden:

1. **Filtros estructurados** (RFC, fechas, montos, tipo, UUID): SQL normal con
   índices. Es el caso de uso principal ("filtro tipo Excel") y lo cubre F4/F5.
   Los vectores serían PEORES aquí: la búsqueda semántica es imprecisa por
   diseño para criterios exactos.
2. **Texto libre** ("gasolina", "honorarios"): **FTS5**, motor de texto completo
   incluido en SQLite (cero dependencias, gratis). Va en F5, indexando las
   descripciones de conceptos.
3. **Semántica** ("materiales de construcción" → encuentra "CEMENTO GRIS CPC
   30R"): `sqlite-vec` almacena/compara vectores, pero NO los genera — se
   necesita un modelo de embeddings. Modelo local = +100–500 MB y complica
   PyInstaller (F9); API en la nube = costo + **enviar datos fiscales de
   clientes a terceros** (choca con la propuesta de confianza de la app y el
   espíritu de la regla e.firma). Por eso F11 es opcional y tardía.

**Cobertura barata desde F4:** el esquema de la bóveda guarda las descripciones
de conceptos en su propia tabla normalizada → agregar FTS5 o sqlite-vec después
es una migración, no un rediseño.

### 5.2 Ediciones Lite / Pro / Top: UN solo código, tres productos (D10)

Habrá tres ediciones comerciales. La arquitectura sostenible para un
desarrollador solo es **un único codebase con compuertas de funcionalidad
(feature gating)** — NUNCA tres repositorios ni tres forks.

- Un único paquete `cfdi_app` contiene TODO el código (parsers, bóveda, SAT,
  módulos). Las ediciones NO son códigos distintos: son la MISMA aplicación con
  funciones habilitadas/deshabilitadas según la edición activa.
- Módulo `editions.py` (nace en F9): matriz declarativa de features por edición.
  Borrador inicial (contenido exacto y precios se deciden al llegar a F9):
  - `LITE`  = { descarga SAT, exportar Excel básico }
  - `PRO`   = LITE + { bóveda, reportes/filtros, validación de estatus }
  - `TOP`   = PRO + { cancelación, analítica nómina, Contabilidad Electrónica/DIOT }
- La edición activa la determina la **licencia en tiempo de ejecución**, no el
  build. Un solo instalador/ejecutable, un solo canal de actualizaciones.
  (Alternativa de tres builds con flags: DESCARTADA — triplica el trabajo de
  release sin beneficio.)
- La UI consulta la matriz: features fuera de la edición se ocultan o se
  muestran deshabilitados con invitación a subir de plan (decisión de UX en F9).
- **Flujo "SAT libera CFDI 4.1/5.0":** agregar `parsers/xml_parser_41.py` + UNA
  rama de despacho (regla intocable §2.1) → una sola release → Lite, Pro y Top
  quedan actualizadas simultáneamente porque comparten el mismo core. Este es
  el requisito explícito del dueño y la regla de aislamiento ya lo garantiza.
- Impacto en F2: NINGÚN trabajo extra — la estructura de paquete modular de §6.1
  es exactamente la separación que el gating necesitará. No implementar gating
  antes de F9.
- Nota realista anti-piratería: el gating por licencia en Python es disuasorio,
  no infranqueable. Suficiente para el mercado objetivo (contadores/PyMEs);
  endurecer solo si el negocio lo justifica.

### 5.3 Nota de diseño a futuro: evolución a shell/dashboard (registrada 2026-07-04)

La GUI actual (`ui/main_window.py`) es una pantalla de propósito único (el
"procesador"). Conforme lleguen módulos con cara propia (F4 bóveda/búsqueda,
F5 reportes, F6 descarga SAT, F7 validación, F8 cancelación), la app
necesitará una capa de navegación — un shell/dashboard con accesos que abran
cada módulo, como en la visión original del dueño (`Roadmap_Aplicacion_CFDI.md`).

- **Estado: dirección registrada, NO es una fase todavía.** Decisión del dueño
  (2026-07-04): el "cuándo" se decide al llegar el segundo módulo con cara
  propia (F4/F5) — fijarlo hoy sería especular.
- **Regla para no pintarse en una esquina mientras tanto:** toda pantalla
  nueva (incluido el visor de F2.5) se construye como **widget autocontenido**
  (no lógica pegada a `MainWindow`), de modo que colgarla de un shell futuro
  sea ensamblaje, no reescritura.

### 5.4 Nota de diseño a futuro: tema claro/oscuro de TODA la app (registrada 2026-07-04)

"Temas claro/oscuro" ya estaba en la visión original del dueño
(`Roadmap_Aplicacion_CFDI.md`, Fase 5 — "Interfaz y experiencia de usuario"),
pero nunca bajó a una fase concreta de F0–F11. Se detectó al construir F2.5
(el dueño notó que la tabla del visor heredaba el tema oscuro de Windows sin
que nadie lo hubiera afinado para lectura de datos).

- **Estado hoy (F2.5):** el `ResultsView` tiene una paleta oscura FIJA
  ("Office/Excel Dark", D16) aplicada solo a ese widget. El resto de la app
  sigue el tema del SO automáticamente (comportamiento por defecto de Qt), sin
  cambios.
- **Lo que falta (NO es una fase todavía):** un sistema real de tema para TODA
  la app — detectar el tema del SO al arrancar, aplicar claro U oscuro de forma
  consistente en cada widget (no solo la tabla), y idealmente permitir
  cambiarlo en caliente si el SO cambia de tema. Esto es sustancialmente más
  trabajo que colorear una tabla: toca la ventana completa, botones, diálogos,
  etc.
- Cuando se construya, la paleta fija de hoy en `ResultsView` deberá
  reconciliarse con el tema activo (para no verse oscura a fuerza si el SO
  está en modo claro). Candidato natural: junto con F9 ("Interfaz y UX") o
  antes si el dueño lo prioriza — el "cuándo" queda abierto a su decisión,
  igual que el shell/dashboard de Sec.5.3.

## 6. Arquitectura de F2 (lo que hay que construir)

### 6.1 Estructura de paquete (migración autorizada por el dueño)

```
cfdi-app/
├── run_gui.bat              → start "" pythonw -m cfdi_app
├── run_gui_debug.bat        → python -m cfdi_app
├── test.bat                 → python -m cfdi_app.cli XML-Test -o test_output.xlsx
├── requirements.txt
├── README.md / PROMPT.md / ROADMAP.md
├── src/cfdi_app/
│   ├── __init__.py
│   ├── __main__.py          # python -m cfdi_app → lanza la GUI
│   ├── paths.py             # ÚNICO dueño de rutas de datos (ver 6.4)
│   ├── log_setup.py         # RotatingFileHandler + sys.excepthook
│   ├── constants.py         # contenido sin cambios
│   ├── core.py              # pipeline sin UI (ver 6.5)
│   ├── cli.py               # modo sin diálogos (hoy cli.py raíz)
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── xml_parser_33.py   # MISMOS nombres, SOLO se mueven. Cero cambios de lógica.
│   │   ├── xml_parser_40.py
│   │   └── pagos_parser_20.py
│   ├── exporters/
│   │   ├── __init__.py
│   │   └── excel_exporter.py  # ver 6.6
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py     # View + máquina de estados (ver 6.2)
│       └── worker.py          # ProcessWorker (QObject)
└── tests/                     # mismas 9 pruebas con imports actualizados + nuevas (ver 6.7)
```

- Los módulos planos de la raíz (`gui.py`, `core.py`, `cli.py`, `constants.py`,
  parsers, exporter) SE MUEVEN al paquete y desaparecen de la raíz.
- `main.py` (Tkinter/consola) SE RETIRA: `cli.py` cubre el uso sin GUI.
  *Decisión reversible; si el dueño pide conservarlo, congelarlo como legacy.*
  **ACLARACIÓN (2026-07-04, hubo confusión):** `main.py` y `cli.py` son DOS
  cosas distintas. `main.py` era el script con diálogo Tkinter de "elegir
  carpeta" — ese es el retirado. `cli.py` NUNCA se eliminó: se movió al
  paquete y sigue vivo (`python -m cfdi_app.cli <carpeta> -o salida.xlsx`,
  sin diálogos). Retiro de `main.py` confirmado por el dueño el 2026-07-04
  (ver D7 y la regla D11 que nació de este episodio).
- Para que `python -m cfdi_app` funcione desde la raíz sin instalar: incluir la
  configuración mínima (pyproject.toml con `pip install -e .`, o ajustar
  sys.path en los .bat — preferir pyproject + editable install).

### 6.2 GUI: máquina de estados explícita (corrección de fondo del Bug 1)

Enum de estados y UN método `_apply_state(state)` que gobierna toda la UI:

```
IDLE ──seleccionar carpeta──▶ READY ──Procesar──▶ PROCESSING ──ok──▶ DONE
                                ▲                     │                │
                                └────── error ───▶ ERROR ◀────────────┘
        (DONE/ERROR → seleccionar otra carpeta o reprocesar → READY/PROCESSING)
```

| Estado | Seleccionar carpeta | Procesar | Guardar Excel… | Barra progreso |
|---|---|---|---|---|
| IDLE | ✅ | ❌ | ❌ | vacía |
| READY | ✅ | ✅ | ❌ | vacía |
| PROCESSING | ❌ | ❌ | ❌ | activa |
| DONE | ✅ | ✅ | ✅ | "Completado" |
| ERROR | ✅ | ✅ | ❌ | "Error" |

**Reglas de oro (documentarlas como comentario en el código):**
1. Los slots conectados a señales del worker/hilo SOLO mutan estado y widgets.
   **JAMÁS abren diálogos modales.**
2. Todo diálogo modal nace de un clic directo del usuario (botón "Guardar
   Excel…", botón "Seleccionar carpeta…"). Un diálogo iniciado por clic siempre
   tiene foco — el clic prueba que la app está en primer plano.
3. En DONE, el resumen (procesados/errores/facturas/nómina/pagos) se muestra
   DENTRO de la ventana (panel o log), no en un QMessageBox.
4. La exportación ocurre en el hilo principal al hacer clic (volúmenes actuales
   son pequeños; si en el futuro tarda, se moverá a worker — no ahora).
5. Tras exportar con éxito: mostrar la ruta en el log con un botón/enlace
   "Abrir" — NO un QMessageBox.question automático.

### 6.3 Hilos: patrón canónico Qt (conexiones exactas)

```
self._thread = QThread(parent=self)      # "_thread": NO sombrear QObject.thread()
self._worker = ProcessWorker(carpeta)
self._worker.moveToThread(self._thread)

self._thread.started         → worker.run
worker.log(str)              → ui.append_log            (queued automático)
worker.progress(int,int,str) → ui.on_progress
worker.finished(object)      → ui.on_result             # guarda resultado, estado DONE
worker.finished              → self._thread.quit
worker.finished              → worker.deleteLater       # se procesa EN el hilo del worker antes de morir
worker.failed(str)           → ui.on_error + self._thread.quit + worker.deleteLater
self._thread.finished        → self._thread.deleteLater
```

Notas: guardar el `ProcessResult` en un atributo (`self._last_result`) para que
el botón "Guardar Excel…" lo use después; poner refs a None en el slot de
`thread.finished` DESPUÉS de los deleteLater (nunca antes de que el hilo muera).

### 6.4 Rutas de datos (`paths.py`) — decisión D4

- Default nuevo: `~/Documents/CFDI-Processor/` con subcarpetas `BovedaCFDI/`,
  `Reports/`, `Logs/`. El nombre "AdminXML" MUERE (era el nombre de la app
  competidora). Usar rutas de usuario reales de Windows (p. ej.
  `QStandardPaths.DocumentsLocation` o expanduser), NO relativas al repo.
- `last_used_directory.txt` vive en la nueva carpeta (o QSettings; elegir uno y
  documentarlo — la configuración completa llega en F3).
- La app NO migra automáticamente datos de `D:\AdminXML` — solo cambia el
  default para lo nuevo. Documentar en README que el usuario puede copiar su
  bóveda manualmente.

### 6.5 `core.py`: errores por archivo

- `ProcessResult` gana `errors: list[tuple[str, str]]` → (ruta del archivo,
  razón legible). `parse_xml_file_by_version` deja de tragar excepciones en
  silencio: captura y devuelve/registra la razón (XML malformado, versión no
  soportada, etc.).
- La GUI muestra en DONE: "X errores — ver detalle en el registro" y lista cada
  archivo fallido en el log. El CLI los imprime.

### 6.6 `excel_exporter.py`

- QUITAR el `try/except Exception` global: las excepciones SE PROPAGAN; la capa
  de UI/CLI decide cómo mostrarlas (caso típico a probar: el .xlsx destino
  abierto en Excel → PermissionError → mensaje claro "cierra el archivo").
- Extraer UN helper `autosize_columns(worksheet, dataframe)` y usarlo 3 veces
  (hoy el bucle está triplicado).
- `print()` → `logging`.

### 6.7 Logging (`log_setup.py`)

- `logging` estándar: RotatingFileHandler en `Documents/CFDI-Processor/Logs/cfdi-app.log`
  (maxBytes ~1MB, 3 backups), formato con timestamp/nivel/módulo.
- `sys.excepthook` global: loguea el traceback completo Y muestra un
  QMessageBox.critical si hay QApplication viva. Con `pythonw` este es el ÚNICO
  ojo sobre crashes.
- Los callbacks `on_log` hacia la UI se mantienen; el archivo es paralelo.

### 6.8 Limpieza de repo

- `git rm -r --cached __pycache__`
- `git rm --cached "CFDI_Processor_App/Reports/*.xlsx"` (contienen RFCs reales)
- Borrar `test_output.xlsx` del tracking si está rastreado.
- Actualizar README.md a la realidad post-F2 (estructura, cómo correr, .bats).

### 6.9 Criterios de aceptación de F2

1. Flujo completo en máquina real Windows: seleccionar carpeta → procesar →
   resumen visible en ventana → clic "Guardar Excel…" → diálogo EN PRIMER
   PLANO → exportar → enlace para abrir. Sin congelamientos, repetible N veces
   sin reiniciar la app.
2. `run_gui.bat` no deja consola; `run_gui_debug.bat` sí la muestra.
3. Con el .xlsx destino abierto en Excel, la app muestra un error claro (no
   éxito falso).
4. Un XML corrupto en la carpeta aparece listado con su razón en el registro.
5. `Documents/CFDI-Processor/Logs/cfdi-app.log` existe y registra la sesión.
6. Suite de pruebas verde (`python -m unittest discover -s tests`), incluyendo
   pruebas nuevas de: transiciones de estado, `ProcessResult.errors`, y que el
   exporter propaga PermissionError.
7. `git ls-files` sin `.pyc` ni `.xlsx`.

## 7. Decisiones registradas (con fecha y por qué)

| # | Decisión | Fecha | Razón |
|---|---|---|---|
| D1 | GUI con **PySide6** (LGPL), NO PyQt6 (GPL/comercial) | 2026-06 | LGPL permite app cerrada/comercial gratis con pip install normal; PyQt6 exigiría pagar u open-sourcear |
| D2 | Front-ends delgados sobre `core.py` único | 2026-06 | Una sola implementación del pipeline para GUI/CLI/futura DB |
| D3 | Alcance F2 = SOLO estabilización (sin SQLite ni settings completos) | 2026-07-01 | Cerrar de verdad F1 antes de abrir F3/F4; decisión del dueño |
| D4 | Datos en `Documents\CFDI-Processor\`; muere el nombre "AdminXML" | 2026-07-01 | Nombre heredado de la app competidora (MiAdminXML); raíz de disco frágil; decisión del dueño |
| D5 | Migración a paquete `src/cfdi_app/` autorizada; parsers conservan nombre y lógica | 2026-07-01 | Escalar a DB/SAT/settings; la regla de aislamiento por versión NO se toca |
| D6 | Distribución (.exe) SIN prisa — solo el dueño usa la app | 2026-07-01 | F9 se dispara cuando aparezca el primer usuario externo |
| D7 | `main.py` (Tkinter) se retira; `cli.py` es el fallback sin GUI. **Confirmada por el dueño 2026-07-04**: no se restaura (los contadores objetivo no usan launchers de bajo nivel). NOTA: `main.py` (picker Tkinter) ≠ `cli.py` (argumentos, sin diálogos) — `cli.py` sigue vivo en `src/cfdi_app/cli.py` | 2026-07-01 | Evitar doble mantenimiento; reversible si el dueño objeta. La ejecución sin consulta previa motivó la regla D11 |
| D8 | Ningún diálogo modal automático; solo por clic del usuario | 2026-07-01 | Corrección de fondo del Bug 1 (modal invisible = app "congelada") |
| D9 | Búsqueda: SQL+índices (F4/F5) → FTS5 (F5) → vectores `sqlite-vec` solo como F11 opcional | 2026-07-01 | El caso de uso real ("filtro tipo Excel") es SQL puro; FTS5 da texto libre gratis y nativo; los embeddings exigen modelo local pesado o API que enviaría datos fiscales a terceros — imprudente hoy. Esquema F4 se diseña para poder agregarlos sin rediseño |
| D10 | Ediciones Lite/Pro/Top = un solo codebase con feature gating por licencia (§5.2); jamás forks separados | 2026-07-01 | Requisito del dueño: al salir CFDI 4.1/5.0, actualizar UN paquete y que las tres ediciones se actualicen a la vez. Un dev solo no puede mantener tres códigos. La regla de aislamiento de parsers ya garantiza el flujo |
| D11 | **REGLA DURA DE PROCESO:** eliminar funcionalidad YA existente y funcionando requiere consultar al dueño ANTES de ejecutar la eliminación — aunque una decisión de diseño previa ya la contemple como "reversible" | 2026-07-04 | D7 se ejecutó en la construcción de F2 sin consulta previa. El dueño no objetó el QUÉ (main.py no vuelve) sino el CÓMO (no se le preguntó antes, ni se le dieron los pros/contras). Diseñar una eliminación no es lo mismo que ejecutarla |
| D12 | El parpadeo cosmético de consola al lanzar `run_gui.bat` se ACEPTA hasta F9; NO se agrega lanzador `.vbs` intermedio | 2026-07-04 | Es `cmd.exe` interpretando el `.bat` antes de que `pythonw` tome control — cosmético, no funcional (el Bug 2 real ya está corregido). El `.exe` de PyInstaller (F9) lo elimina por diseño. Decisión del dueño. NO volver a reportarlo como bug |
| D13 | El Visor de resultados (MUST del dueño) se construye YA como fase **F2.5**, con patrón **Model/View obligatorio** (`QTableView` + `QAbstractTableModel`; `QTableWidget` PROHIBIDO). Sin SQLite y sin andamiaje de repositorios extra | 2026-07-04 | Ver totales (subtotal/descuento/IVA/total) sin abrir Excel es estándar en las herramientas competidoras. El modo "lote actual" NO es desechable: sigue siendo útil después de F4 ("muéstrame lo que acabo de procesar"); F4 solo AGREGA el modo historial/periodos sobre la MISMA vista. El andamiaje SQLite anticipado se descartó por sobre-ingeniería: la frontera del modelo Qt ya es la costura donde F4 se conectará |
| D14 | Memoria de la ruta de GUARDADO del Excel: F2.5 siembra un `settings.json` mínimo (recordar última carpeta de guardado, comportamiento por defecto); el checkbox "usar siempre la misma ruta fija" y el resto de la configuración llegan en F3 SOBRE ese mismo mecanismo | 2026-07-04 | Gap de UX detectado por el dueño en las pruebas reales de F2 (el diálogo siempre proponía Reports e ignoraba dónde guardó la última vez). Un solo mecanismo de settings: F3 extiende, no duplica; el `last_used_directory.txt` actual se absorbe como clave `last_input_dir` del mismo `settings.json` |
| D15 | F2.5 incluye un filtro incremental (caja de búsqueda única) sobre el lote actual: texto libre (subcadena, sin distinguir mayúsculas) contra RFC Emisor/Receptor, Nombre Emisor/Receptor, Factura (Serie+Folio), UUID y **Conceptos** (descripción de línea) — MÁS comparación numérica con operadores `<`,`>`,`<=`,`>=` sobre montos, **columna por defecto: Total** (no Subtotal). Los totales se recalculan sobre las filas visibles tras filtrar | 2026-07-04 | El dueño pidió poder buscar "tela" en el concepto de una factura sin recordar RFC/nombre del proveedor, y filtrar por monto (`<2000`) para revisar deducibilidad. Se verificó en datos reales que `Nombre Emisor`, `Nombre Receptor` y `Conceptos` YA son strings planos en cada registro (`Conceptos` = concatenación de descripciones con `' \| '`) — el "texto libre en varias columnas" cuesta lo mismo que buscar solo por RFC, no es una versión "más compleja". El operador numérico sí es un mecanismo aparte (comparación, no substring) pero igual de barato dado el `QSortFilterProxyModel` ya mandatado (D13). Default a Total (no Subtotal) por confirmación explícita del dueño, con base en criterio fiscal práctico, no en la costumbre heredada de un exsocio |
| D16 | Paleta **"Office/Excel Dark"** (`#201F1E` fondo, `#292827` fila alterna, `#E8E6E3` texto, `#323130`/`#FFFFFF` encabezado, `#004E8C` selección) aplicada como stylesheet **SOLO al `ResultsView`** (la tabla del visor) — NO es un tema de toda la app. El alcance de "campos buscables" del filtro (D15) NO se amplía en F2.5; queda igual, abierto a que el dueño pida agregar un campo puntual cuando haga falta | 2026-07-04 | El dueño pidió una paleta oscura legible sin que yo eligiera por él — se presentaron 4 opciones investigadas (VS Code Dark+, Material Dark, Solarized Dark, Office/Excel Dark) con sus hex y su razón de ser; eligió Office/Excel por familiaridad de sus usuarios contadores con el modo oscuro de Excel. Confirmó explícitamente NO ampliar el alcance del filtro ahora, solo dejarlo abierto a futuro |
| D17 | Columna **"Conceptos" agregada como VISIBLE** en las pestañas Facturas y Nómina del visor (antes solo era buscable, no visible) | 2026-07-04 | Gap real detectado por el dueño: el filtro ya buscaba en Conceptos (encontraba "CFE" al escribir "energía"), pero al no ser columna visible no se podía ver POR QUÉ una fila coincidió. Todo campo que sea parte del filtro debe poder verse en la tabla |
| D18 | Columnas VISIBLES del visor: **AMBAS cosas** — (1) default curado ampliado YA en F2.5 (Facturas 12→23, Nómina 11→19, Pagos 9→17, de un total de 62/~98/115 disponibles); (2) selector de columnas configurable por el usuario **construido en F3**, persistido en `settings.json`. Una columna sin dato en un registro dado queda simplemente EN BLANCO para esa fila (comportamiento estándar de cualquier hoja de cálculo) — NO se oculta/muestra columna por fila; eso sería un mecanismo distinto y no es lo que se pidió | 2026-07-04 | El dueño necesita ver hoy campos que antes no estaban (p. ej. UUID Relación, retenciones, forma/método de pago) sin esperar a F3, pero reconoce que el default curado nunca va a cubrir todos los casos de uso de todos los meses — de ahí que el selector configurable siga siendo necesario después. Todos los nombres de columna nuevos se verificaron contra datos reales (Facturas/Nómina) y contra `PAGOS_COLUMN_ORDER` (Pagos, sin fixtures de prueba) antes de aceptarlos — cero columnas fantasma |

## 8. Instrucciones para modelos constructores (de cualquier fase)

1. Lee este archivo completo + `PROMPT.md` antes de tocar código.
2. Respeta las reglas intocables (§2). Los parsers SOLO se mueven de carpeta.
3. Construye en pasos pequeños y ejecutables; corre la suite tras cada paso.
4. Verifica el hilo REAL (no solo offscreen con diálogos simulados — así se
   escapó el Bug 1): pide al dueño probar en su máquina antes de dar una fase
   por cerrada. Los criterios de aceptación de la fase son la definición de
   "hecho".
5. El dueño es hispanohablante, desarrollador solo, y quiere validar decisiones:
   pregunta antes de desviarte de este documento.
6. **REGLA DURA (D11):** NUNCA elimines funcionalidad ya existente y
   funcionando sin consultar al dueño ANTES de ejecutar la eliminación —
   aunque este documento la marque como decidida o "reversible". Diseñar una
   eliminación no es lo mismo que ejecutarla: la ejecución siempre se
   confirma primero con el dueño.

## 9. Resultado de F2 (construida 2026-07-03)

F2 se construyó completa siguiendo §6. Resumen de lo que cambió respecto al
diseño (todo alineado, sin desviaciones de fondo):

- **Estructura de paquete**: `src/cfdi_app/` con `parsers/`, `exporters/`,
  `ui/` (`state.py`, `worker.py`, `main_window.py`), `paths.py`, `log_setup.py`,
  `core.py`, `cli.py`, `__main__.py`. `pyproject.toml` con `src/` layout;
  instalado con `pip install -e .`. Los 3 parsers y `constants.py` se movieron
  con `git mv` — solo cambió su línea de import (`from cfdi_app.constants
  import ...`), cero cambios de lógica. `main.py` (Tkinter) retirado (D7,
  confirmado por el dueño 2026-07-04). **Precisión importante:** `cli.py` NO se
  eliminó — el archivo de la raíz se movió al paquete y sigue funcionando como
  `src/cfdi_app/cli.py`; `gui.py`/`core.py` de la raíz fueron reemplazados por
  sus equivalentes dentro del paquete. Lo único retirado de verdad fue
  `main.py` (el picker Tkinter).
- **Bug 1 (corrección de fondo):** implementada la máquina de estados de §6.2
  como módulo Qt-free (`ui/state.py`, función pura `widget_states_for`). El
  botón **"Guardar Excel…"** solo se habilita en estado DONE y su diálogo nace
  del clic del usuario — nunca se abre automáticamente desde un callback de
  hilo. Se agregó un botón explícito **"Abrir archivo"** (habilitado tras
  guardar) en vez del `QMessageBox.question` automático original.
- **Bug 2 (corrección):** `run_gui.bat` → `start "" pythonw -m cfdi_app`;
  nuevo `run_gui_debug.bat` → `python -m cfdi_app` con consola. `log_setup.py`
  implementado (RotatingFileHandler + `sys.excepthook`) como prerequisito.
- **Rutas de datos (D4):** `paths.py` resuelve a
  `~/Documents/CFDI-Processor/{BovedaCFDI,Reports,Logs}` — verificado en esta
  máquina: `BASE_APP_DIR = C:\Users\<usuario>\Documents\CFDI-Processor`.
- **Errores por archivo (§6.5):** `parse_xml_file_by_version` ahora devuelve
  `(data, error_message)`; `ProcessResult.errors` lista cada archivo fallido
  con su razón. Se corrigió además un defecto no listado originalmente: un
  `.zip` corrupto (`BadZipFile`) antes tumbaba TODO `process_path` sin control;
  ahora se reporta como error de ese zip y el resto de la corrida continúa.
- **`excel_exporter.py` (§6.6):** se quitó el `try/except` global (las
  excepciones se propagan); se extrajo `autosize_columns()` como helper único
  (antes triplicado); `print()` → `logging`.
- **Limpieza de repo (§6.8):** `git rm -r --cached __pycache__`; se retiró del
  tracking (y del disco) todo `CFDI_Processor_App/` — contenía 7 reportes
  `.xlsx` con un RFC de apariencia real (`GOOH841231EPA`) y un
  `last_used_directory.txt`. El historial de git aún conserva esos datos; si el
  repo se comparte públicamente algún día, evaluar `git filter-repo` para
  purgarlos del historial también. `.gitignore` actualizado.
- **Pruebas:** 22 verdes (`python -m unittest discover -s tests`) — las 9
  originales + 13 nuevas: transiciones de la máquina de estados
  (`tests/test_ui_state.py`), errores por archivo incluyendo XML corrupto,
  versión no soportada y ZIP dañado (`tests/test_core.py`), y propagación de
  `PermissionError` del exporter (`tests/test_exporter.py`).
- **README.md** actualizado a la estructura y flujo post-F2.

### Verificación realizada (y su límite honesto)

Se ejecutó un end-to-end headless (`QT_QPA_PLATFORM=offscreen`) usando un
**QThread real** (no una llamada síncrona al worker, que es como se escapó el
Bug 1 la vez anterior): seleccionar carpeta → Procesar → esperar el hilo real →
Guardar Excel → Abrir archivo → reprocesar sin reiniciar. Se instrumentó un
"guardia anti-Bug-1" que hace fallar la prueba si CUALQUIER diálogo modal se
abre fuera de un clic explícito del usuario — no se disparó ninguno.

**Límite honesto:** esto corre en modo offscreen (sin ventana visible real de
Windows). El síntoma original del Bug 1 involucraba específicamente el
comportamiento de foco/z-order de diálogos nativos de Windows, que offscreen no
puede reproducir al 100%. Por eso el **criterio 6.9.1 permanece abierto**: el
dueño debe correr `run_gui.bat` en su máquina real y confirmar el flujo
completo antes de considerar F2 verdaderamente cerrada. Si algo sigue fallando
ahí, revisar primero `Documents\CFDI-Processor\Logs\cfdi-app.log`.

### Cierre de F2 — CONFIRMADO por el dueño (2026-07-04)
- [x] Windows real: `run_gui.bat` no deja consola (solo el parpadeo cosmético
  de `cmd.exe`, aceptado — ver D12); el flujo completo (seleccionar → procesar
  → guardar → abrir) no se congela y es repetible sin reiniciar la app —
  el dueño corrió múltiples procesos seguidos.
- [x] Prueba de bloqueo de Excel: guardar un reporte DISTINTO teniendo otro
  archivo abierto en Excel funcionó sin falso error; guardar sobre EL MISMO
  archivo abierto mostró correctamente el mensaje de archivo
  bloqueado/abierto. Comportamiento exactamente el esperado (criterio 6.9.3).
- [x] Siguiente fase decidida: ver tabla de fases §5 (decisión del visor,
  D13/D14).

**F2 está cerrada al 100%. Bug 1 y Bug 2: resueltos y confirmados.**

## 10. Backlog de UX (registrado, SIN acción por ahora)

Observaciones del dueño en las pruebas reales de F2. Se registran para pulido
futuro (probablemente junto con settings en F3, o al probar con más
contadores). NO son bugs; NO actuar sin que el dueño lo pida.

1. **Abrir archivo tras guardar:** hoy es un botón explícito ("Abrir archivo"),
   por diseño anti-Bug-1 (D8). Funciona, pero algunos contadores quizá
   prefieran que el sistema pregunte automáticamente al terminar de guardar.
   Candidato a preferencia configurable ("preguntar al terminar: sí/no") cuando
   exista el sistema de settings (F3). Decidir idealmente con feedback de
   usuarios reales.
2. **Parpadeo del `.bat` al lanzar:** decisión tomada (D12) — se acepta hasta
   el `.exe` de F9. No re-reportar.
3. **Ruta de guardado del Excel:** resuelto en diseño (D14) — memoria en F2.5,
   checkbox en F3.
4. **Orden/disposición de los botones:** el dueño comentó que el flujo se
   siente "un poco directo" con el orden actual de botones. Sin propuesta
   concreta aún; revisar cuando el visor (F2.5) reorganice la ventana de todos
   modos.

## 11. Arquitectura de F2.5 — Visor de resultados (SIGUIENTE FASE A CONSTRUIR)

Decidida por el dueño el 2026-07-04 (D13, D14). Alcance deliberadamente corto.
El modelo constructor debe leer también §8 (reglas para constructores, incluida
la regla dura D11) y §6.2 (reglas de oro anti-Bug-1, que siguen vigentes).

### 11.1 Entrega

Dentro de la GUI existente, al terminar un procesamiento (estado `DONE`):

1. **Tabla de resultados del lote actual**, con pestañas espejo de las hojas
   del Excel (Invoices / Nómina / Pagos), reutilizando los órdenes de columna
   de `constants.py`. Columnas visibles mínimas en Invoices: Tipo, RFC Emisor,
   RFC Receptor, Fecha, Subtotal, Descuento, IVA (o total de impuestos), Total,
   UUID. Los datos salen del `ProcessResult` que ya vive en memoria
   (`_last_result`) — NO se re-parsea nada.
2. **Fila/panel de TOTALES por pestaña**: suma de Subtotal, Descuento, IVA y
   Total de los registros **visibles tras aplicar el filtro** (ver punto 5).
   Formato de moneda mexicana.
5. **Filtro incremental (D15)**: una sola caja de búsqueda arriba de la tabla.
   - Texto libre → subcadena (case-insensitive) contra RFC Emisor, Nombre
     Emisor, RFC Receptor, Nombre Receptor, Factura, UUID, Conceptos.
   - Empieza con `<`, `>`, `<=`, `>=` seguido de un número → comparación
     numérica sobre **Total** (default) o la columna nombrada explícitamente
     (p. ej. `subtotal<2000`).
   - La lógica de coincidencia (`matches_search`) y de sumas
     (`compute_totals`) vive en un módulo **Qt-free**, testeable sin ventana
     (mismo patrón que `ui/state.py`); el `QSortFilterProxyModel` solo la
     invoca.
3. **Botón "Abrir carpeta"**: abre en el Explorador la carpeta contenedora del
   Excel guardado (disponible junto a "Abrir archivo", misma condición de
   habilitación). Cubre el caso "solo quiero llegar al archivo, no abrirlo".
4. **`settings.json` mínimo** en la carpeta de datos de la app (D14):
   - `last_input_dir` — absorbe el `last_used_directory.txt` actual (migrarlo
     y retirar el .txt; esto es un reemplazo de mecanismo interno, no una
     eliminación de funcionalidad visible — la funcionalidad se conserva).
   - `last_save_dir` — nueva: al guardar un Excel con éxito, se recuerda esa
     carpeta y el siguiente "Guardar Excel…" la propone como default. Si no
     existe aún, se propone `Reports` como hoy.

### 11.2 Restricciones duras

- **D13 — Model/View obligatorio:** `QTableView` + `QAbstractTableModel`
  (subclase propia alimentada por listas de dicts del `ProcessResult`).
  **`QTableWidget` PROHIBIDO** — metería los datos dentro del widget y ese
  trabajo sí sería desechable en F4.
- La vista NO debe conocer la fuente de datos: en F4 se conectará un segundo
  modelo (respaldado por SQLite) a la MISMA vista para el modo
  historial/periodos. El modo "lote actual" se conserva post-F4.
- **§5.3 — widget autocontenido:** el visor se construye como widget propio
  (p. ej. `ui/results_view.py`), no como lógica pegada dentro de
  `MainWindow`, para poder colgarlo de un shell futuro sin reescribir.
- Las reglas de oro anti-Bug-1 (§6.2) siguen aplicando: ningún diálogo modal
  automático; "Abrir carpeta" nace de un clic.
- NADA de SQLite en esta fase (ni esquema, ni repositorios anticipados).

### 11.3 Criterios de aceptación de F2.5

1. Tras procesar, la tabla muestra los registros del lote con sus pestañas, y
   las SUMAS coinciden con las del Excel exportado (verificar contra un lote
   real de XML-Test).
2. "Abrir carpeta" abre el Explorador en la carpeta del último Excel guardado.
3. Guardar en una carpeta distinta → el siguiente "Guardar Excel…" propone esa
   carpeta (persiste entre sesiones vía `settings.json`).
4. `last_used_directory.txt` migrado a `settings.json` sin perder el valor; la
   carpeta de entrada se sigue recordando igual que antes.
5. Suite verde con pruebas nuevas: el modelo de tabla (conteos y sumas
   correctas por tipo) y la lógica de settings (leer/escribir/migrar) — ambas
   probables sin ventana real.
6. Confirmación del dueño en máquina real (regla §8.4), incluyendo re-procesar
   varias veces y verificar que la tabla se actualiza con cada lote.

## 12. Resultado de F2.5 (construida 2026-07-04)

F2.5 se construyó completa siguiendo §11, en pasos chicos con pruebas entre
cada uno (tal como pidió el dueño para poder revisar/administrar por partes).

- **`ui/filtering.py`** (Qt-free, D15): `matches_search()` resuelve las dos
  sintaxis de la caja de búsqueda — subcadena de texto sobre
  RFC Emisor/Receptor, Nombre Emisor/Receptor, Factura, UUID y **Conceptos**
  (se verificó con datos reales que `Nombre Emisor/Receptor` y `Conceptos` ya
  son strings planos en cada registro — el texto libre no costó nada extra);
  o comparación numérica (`<`, `>`, `<=`, `>=`) sobre un alias de campo
  opcional, con **Total** como default (D14/D15 — decisión explícita del
  dueño, no la costumbre heredada de "Subtotal"). Alias no reconocido degrada
  a búsqueda de texto en vez de fallar. `compute_totals()` suma solo sobre los
  registros ya filtrados.
- **`ui/results_model.py`** / **`ui/results_proxy.py`**: `RecordTableModel`
  (`QAbstractTableModel` genérico, reutilizado para Invoices/Nómina/Pagos) +
  `RecordFilterProxyModel` (`QSortFilterProxyModel` delgado que solo LLAMA a
  `matches_search()` — no reimplementa lógica). Cumple D13 al pie de la letra;
  `QTableWidget` no se usó en ningún punto.
- **`ui/results_view.py`**: `ResultsView` (autocontenido, sin conocer
  `MainWindow` — cumple la regla de §5.3) con 3 pestañas (`TabConfig` por tipo
  de documento), cada una con caja de búsqueda + tabla + fila de totales.
  Nota de implementación: Pagos usa nombres de columna distintos
  (`RFC Emisor CFDI`, `MontoTotalPagos`, sin campo `Conceptos`) — cada pestaña
  tiene su propia configuración de campos, no se asumió un esquema único.
- **`settings.py`** (D14): `settings.json` en `Documents/CFDI-Processor/` con
  `last_input_dir` y `last_save_dir`. Migra una sola vez el
  `last_used_directory.txt` legado de `paths.py` (sin borrarlo — queda como
  fósil inofensivo). Corrupción del JSON cae a defaults sin tronar.
- **`core.py`**: nuevo `open_containing_folder()` (Explorador con el archivo
  seleccionado en Windows vía `explorer /select,`, con fallback a solo abrir
  la carpeta).
- **`ui/main_window.py`**: agrega el `ResultsView` a la ventana (visible en
  estado DONE, se llena en `on_result()` — ANTES de que exista cualquier
  `.xlsx`, tal como pidió el dueño), botón nuevo "Abrir carpeta", y el diálogo
  de "Guardar Excel…" ahora propone `settings.get_last_save_dir()` en vez de
  siempre `Reports`. `paths.read_last_used_directory/save_last_used_directory`
  quedan sin usar por la GUI (reemplazados por `settings.py`) pero NO se
  borraron del archivo — decisión conservadora, no rompen nada al quedar ahí.
- **Pruebas:** 57 verdes (las 22 de F2 + 35 nuevas): `test_filtering.py` (15,
  incluye el caso real "buscar tela sin saber el RFC"), `test_settings.py` (9,
  con aislamiento de directorio temporal — nunca toca el `settings.json` real
  del usuario), `test_results_view.py` (11, modelo/proxy/vista con datos reales
  de `XML-Test`).

### Verificación realizada (mismo estándar que F2)

End-to-end headless con **QThread real** (no simulado): seleccionar carpeta →
Procesar → visor se llena con 8 facturas → filtrar "pintura" reduce a 2 con
totales recalculados → Guardar Excel (propone y usa la carpeta temporal
simulando una ruta ya usada) → botones "Abrir archivo"/"Abrir carpeta" se
habilitan y se invocan con la ruta correcta → `settings.json` contiene
`last_input_dir` y `last_save_dir` correctos → reprocesar sin reiniciar la
app. Guardia anti-Bug-1 activo durante toda la corrida: cero diálogos
automáticos.

**Límite honesto (igual que en F2):** verificado en modo offscreen, no en una
ventana visible de Windows. El criterio de aceptación #6 (confirmación del
dueño en máquina real) sigue abierto.

### Pendiente para cerrar F2.5 al 100%
- [ ] Dueño confirma en Windows real: el visor aparece tras procesar (antes de
  guardar cualquier Excel), el filtro por concepto/monto funciona y los
  totales se ven correctos, "Abrir carpeta" abre el Explorador en el lugar
  correcto, y guardar dos veces en carpetas distintas hace que la segunda vez
  proponga la última usada (no siempre Reports).
- [ ] Dueño confirma visualmente la paleta "Office/Excel Dark" (D16) en la
  tabla del visor y que el número de fila queda 1..N tras ordenar (ver abajo).
- [ ] Decidir con el dueño la siguiente fase: F3 (directorio de trabajo +
  auto-organización) o F4 (bóveda SQLite).
- [x] Enfoque de columnas visibles decidido (D18): default ampliado YA
  (Facturas 12→23, Nómina 11→19, Pagos 9→17) + selector configurable por el
  usuario en F3. Ver detalle de qué se incluyó/excluyó y por qué en los
  comentarios de `ui/results_view.py` junto a cada `TabConfig`.

### Ronda 2 de ajustes (mismo día, tras la primera prueba real del dueño)

El dueño probó F2.5 en su máquina y reportó 4 puntos; se resolvieron 3 de
inmediato (bugs/decisiones sin ambigüedad) y 1 quedó como decisión abierta:

1. **Bug real corregido:** el número de fila (encabezado vertical) quedaba
   desordenado al ordenar una columna (mostraba p. ej. "2, 3, 1" en vez de
   "1, 2, 3"). Causa: comportamiento por defecto de `QSortFilterProxyModel`,
   que resuelve el encabezado vertical vía `mapToSource()` — el número queda
   pegado a la posición ORIGINAL, no a la visual. Corregido en
   `RecordFilterProxyModel.headerData()` devolviendo la posición visual
   directamente para `Qt.Vertical`, sin pasar por el modelo fuente. Prueba de
   regresión agregada (`test_vertical_header_stays_sequential_after_sorting`).
2. **Gap real corregido (D17):** "Conceptos" ya era buscable pero no visible
   en Facturas/Nómina — agregado a `display_columns` de ambas pestañas.
3. **Paleta aplicada (D16):** "Office/Excel Dark" vía stylesheet Qt (QSS)
   scopeado únicamente al `ResultsView` (no a la app completa).
4. **Nota de tema completo registrada** (Sec.5.4): un sistema de tema
   claro/oscuro para TODA la app (con autodetección del SO) ya estaba en la
   visión original (`Roadmap_Aplicacion_CFDI.md`) pero nunca tuvo fase — ahora
   está anotado explícitamente, sin fase asignada todavía.
5. **Bug real corregido — la ventana ya no se podía encoger:** tras ampliar
   columnas (D18), el dueño notó que la ventana dejó de poder reducirse de
   tamaño. Causa real (verificada midiendo `minimumSizeHint()` capa por capa,
   NO era la tabla): `totals_label` (la fila de totales) se creaba SIN
   `setWordWrap(True)`, así que Qt calculaba el ancho mínimo de la ventana
   como el necesario para mostrar TODA la línea de totales sin cortar — con
   7 columnas de totales en Facturas, eso forzaba un mínimo de **1924px**.
   Corregido activando `setWordWrap(True)` en `totals_label`
   (`ui/results_view.py`): el mínimo bajó a **958px**, la ventana vuelve a
   encogerse libremente y el texto se acomoda en varias líneas cuando hace
   falta en vez de bloquear el resize.

**Pregunta abierta que quedó pendiente de la respuesta del dueño:** para las
columnas VISIBLES en la tabla (no el filtro, que se queda igual por D15/D16),
¿F2.5 amplía el default curado ahora (más allá de los ~11 actuales, sin
llegar a las 62 del Excel), y/o se construye en F3 un selector de columnas
configurable por el usuario (checkboxes, persistido en `settings.json`)? Este
selector es una función real de UI (comparable en tamaño a lo ya construido
en F2.5), no un ajuste barato como ampliar `text_fields`.
