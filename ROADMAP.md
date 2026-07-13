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
| F2.5 | Visor de resultados en la GUI | Tabla del lote procesado con pestañas espejo del Excel (Invoices/Nómina/Pagos) + fila de TOTALES (subtotal, descuento, IVA, total) + botón "Abrir carpeta" + `settings.json` mínimo que recuerda la última carpeta de guardado (D14) + filtro incremental (D15). **Restricción dura D13: Qt Model/View — `QTableView` + `QAbstractTableModel`; `QTableWidget` PROHIBIDO.** Sin SQLite. Definición completa en §11 | F2 | ✅ **CERRADA** — construida y confirmada por el dueño en máquina real 2026-07-04, con 3 rondas de ajustes (ver §12) |
| F2.6 | Captura de campos faltantes (parsers, UNA sola ola) | Alcance completo definido por la auditoría §13.2 + §13.5: núcleo (InformacionGlobal, TipoRelacion, `RegimenFiscal Emisor` al Excel) + **3 bugs** (typo `TotalTrasladadoBaseIVAExento`→`TotalTrasladosBaseIVAExento`; bug estructural de Pagos que nulificaba TODOS los Totales, D27; clave muerta `15101501` → 35 claves oficiales familia 1510) + "Total Sueldos" resuelto con D26 + IEDU (`autRVOE`, `rfcPago`) + Nómina (NumDiasPagados, TipoContrato, TipoRegimen, NumEmpleado, etc.) + **captura por-concepto EN MEMORIA según el contrato de §14.5 (D25)**: `ConceptosDetalle` y los `*Detalle` de Nómina. Detalle completo del resultado en §15 | F2.5 ✅ + XSDs ✅ + diseño F4 §14 ✅ | ✅ **CONSTRUIDA** 2026-07-04 (ver §15) — falta confirmación del dueño en máquina real |
| **F2.7** | **Exportación filtrada "espejo del visor"** | Botón nuevo "Guardar filtrado…" (el actual NO cambia): cada hoja del Excel sale según SU propio filtro de pestaña — filtradas recortadas, sin filtro completas. Sufijo derivado del query sanitizado (`_Filtrado_tela`, `_Filtrado_menor2000`; fallback `_Filtrado` si hay varios filtros o queda vacío). Garantía de fidelidad: exportado ≡ visible, probado. Diseño completo en §16 (evaluación crítica incluida — no se aceptó en automático) | F2.5 ✅ (reusa `filter_records`) | ⬅️ **LISTA PARA CONSTRUIR** (diseñada 2026-07-05, D29) |
| **F2.8** | **Reporte fiscal "Papel de trabajo" (edición Pro)** | Hojas nuevas al final del MISMO Excel: PT-Recibidas (resumen mensual IVA-flujo + detalle con semáforos de deducibilidad y columna manual "Conciliado banco"), PT-Emitidas (resumen + por cliente/CxC), hoja Fundamentos (citas legales verificadas + disclaimer). Gate de edición provisional default "todo habilitado" (D30, matiza D10). Diseño completo en §17 (D30–D35) | F2.7 (orden de etapas pedido por el dueño) + F2.6 ✅ (usa `ConceptosDetalle`) | **DISEÑADA** 2026-07-05 — construir DESPUÉS de F2.7 |
| F3 | Directorio de trabajo + auto-organización | Settings persistentes (EXTIENDE el `settings.json` sembrado en F2.5, no crea otro mecanismo), checkbox "usar siempre la misma ruta de guardado" (D14), **selector de columnas visibles del visor** (checkboxes, persistido — D18), selector de working dir, archivado `BovedaCFDI\{RFC}\{Emitidas|Recibidas}\{YYYY}\{MM}` (año/mes = fecha de timbrado) | F2.5 | Pendiente |
| F4 | Bóveda SQLite | Parseo único, metadatos en DB, dedup por UUID, búsqueda. **Diseño técnico COMPLETO en §14** (2026-07-04): esquema híbrido relacional+JSON elástico (D24), tablas cfdi/conceptos/nomina/pagos/pagos_doctos, política de migraciones aditivas, campo nuevo = cero migración | F2 (diseño ✅; construcción pendiente) | Pendiente |
| F5 | Reportes y filtros | Tablas Qt Model/View + **búsqueda de texto FTS5** (nativa de SQLite) sobre descripciones de conceptos + **filtro por periodo formalizado (D21)**: día, mes, año Y rango personalizado (campos "desde–hasta"), SIEMPRE consultando la bóveda SQLite — **JAMÁS recorriendo carpetas**. **Jerarquía dura de alcance (D21): 1º RFC, 2º Emitidas/Recibidas — todo filtro opera dentro de un RFC y una dirección ya elegidos; NUNCA se mezclan RFCs ni direcciones en un mismo resultado** | F4 | Pendiente |
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

### 5.5 Limitaciones estructurales del CFDI (registradas 2026-07-04, D22)

Dos casos donde la limitación NO es "falta una columna" sino la naturaleza
misma del CFDI. Se documentan para que nadie los re-reporte como bugs ni
prometa resolverlos con más campos:

1. **Detección de combustible = inferencia, no certeza.** El CFDI no tiene un
   campo booleano "EsCombustible"; se infiere del producto/servicio. Hoy la
   heurística es débil (4 códigos hardcodeados + palabras clave). Con el
   catálogo oficial completo `c_ClaveProdServ` (pendiente de que el dueño suba
   `catCFDI.xls`, ver §13) y la captura por-concepto (F2.6/F4), la detección
   se vuelve **casi determinista**: exacta cuando el emisor clasificó bien su
   clave. El riesgo residual queda solo en emisores que usan una clave
   genérica/incorrecta — eso es un error del emisor, incorregible desde aquí.
   Nivel de confianza esperado post-F2.6: alto, no absoluto.
2. **Un REP/CFDI de Pagos NO prueba que el dinero se movió.** Un CFDI de
   Pagos 2.0 es una DECLARACIÓN fiscal de que un pago se recibió/aplicó; un
   PUE es lo que el comprobante dice. La confirmación real de que el dinero
   "cayó" solo existe en el estado de cuenta bancario — una fuente de datos
   completamente ajena al CFDI y fuera del alcance de TODAS las fases
   actuales. **Conciliación bancaria** (importar estados de cuenta, nuevo
   formato de entrada, matching heurístico pago↔movimiento) sería una función
   de un orden de magnitud distinto: queda registrada como dirección futura
   posible SIN fase asignada, igual que 5.3/5.4. No prometer verificación de
   pagos "reales" en ninguna edición mientras esto no exista.

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
| D19 | Alcance de la auditoría de campos (§13): SOLO los 4 complementos en uso (Nómina 1.2, Pagos 2.0, IEDU, ImpLocal). Carta Porte, Comercio Exterior y auditoría del 3.3 quedan FUERA deliberadamente, sin preparación anticipada, con disparador documentado: primer cliente real que lo necesite | 2026-07-04 | Costo/beneficio del dueño: Carta Porte lo usan corporativos con ERP propio; CCE sin clientes hoy; 3.3 solo para auditorías fiscales históricas improbables. El aislamiento por versión hace que agregarlos después sea costo acotado (módulo nuevo + rama de despacho); preparar hoy sería gastar procesamiento en algo que quizá nunca se use |
| D20 | Los campos faltantes se capturan en **UNA sola ola (fase F2.6)**, tras terminar la auditoría de complementos con los XSD. **Prerequisito duro: tag git de respaldo antes de tocar cualquier parser** — creado `v0.2.5-estable` (2026-07-04, árbol limpio, 58 pruebas verdes) como punto de restauración con nombre | 2026-07-04 | Elección del dueño: un solo cambio + un solo retesteo, no dos olas. Su condición explícita fue asegurar el respaldo "de cuando funcionaba"; git ya lo tenía committeado y el tag lo hace restaurable por nombre. Modificar `xml_parser_40.py` NO viola la regla de aislamiento (esta prohíbe fusionar versiones, no mantener el parser vigente), pero por D11 se consultó explícitamente |
| D21 | Filtro por periodo (F5): granularidad día/mes/año + rango personalizado "desde–hasta". SIEMPRE consulta la bóveda SQLite; **JAMÁS recorre la estructura de carpetas** (las carpetas RFC/Emitidas·Recibidas/Año/Mes son para humanos; la DB para consultas). **Jerarquía dura: 1º RFC, 2º Emitidas/Recibidas — nunca se mezclan RFCs ni direcciones en un mismo resultado** | 2026-07-04 | Preocupación del dueño: filtrar periodos con la estructura de carpetas obligaría a "cd ../.." entre meses. La respuesta de diseño es que el archivado físico y la consulta son capas independientes (para eso existe F4). La jerarquía RFC→dirección es requisito explícito e inflexible del dueño |
| D22 | Limitaciones estructurales del CFDI documentadas (§5.5): (1) detección de combustible = inferencia, casi determinista con catálogo oficial + captura por-concepto, pero nunca absoluta; (2) REP/Pagos ≠ confirmación bancaria — verificar que el dinero "cayó" requiere estados de cuenta (fuente ajena al CFDI), fuera del alcance de todas las fases; conciliación bancaria queda como dirección futura sin fase | 2026-07-04 | Distinguir "falta un campo" (arreglable en F2.6) de "el CFDI no contiene esa verdad" (no arreglable con columnas). Evita re-reportes como bugs y promesas comerciales imposibles |
| D23 | Auditoría de complementos COMPLETA (§13.5) con los 5 archivos oficiales recibidos; F2.6 desbloqueada con alcance cerrado. El `catCFDI.xsd` (sin descripciones) es SUFICIENTE para F2.6 — el `catCFDI.xls` con descripciones queda como opcional futuro, no bloquea nada. Referencia programática generada en `docs/sat-esquemas-referencia.md` | 2026-07-04 | La auditoría encontró 2 bugs reales que ningún reporte de usuario había detectado (typo de atributo que deja una columna siempre en 0.00; clave de combustible inexistente en el catálogo oficial) — evidencia de que auditar contra fuente autoritativa, y no de memoria, era el método correcto |
| D24 | **Bóveda F4 = SQLite híbrido relacional+JSON con política de elasticidad (§14). MongoDB DESCARTADO definitivamente** (local o Atlas). El esquema evoluciona con: campo nuevo→JSON `extras` sin migración; campo caliente→promoción aditiva (ADD COLUMN + backfill); migraciones numeradas SOLO aditivas (`user_version`); respaldo automático del .db antes de migrar | 2026-07-04 | El dueño preguntó explícitamente por evolución tipo MongoDB ("agregar sin que se rompa nada"). Mongo falla por privacidad (datos fiscales en nube de terceros — misma lógica de D9), empaque (servidor aparte imposible para contadores no técnicos) y capacidad (free tier 512MB vs 200k+ XMLs). El híbrido SQLite da esa elasticidad CON poder SQL. Capacidades verificadas EN VIVO en la máquina del dueño (SQLite 3.50.4): JSON, ADD COLUMN no destructivo, índices de expresión, user_version |
| D25 | Contrato de captura por-concepto para F2.6 (§14.5): listas de **dicts Python nativos** (no JSON pre-serializado) con **claves = nombres oficiales del XSD tal cual** — `ConceptosDetalle` en facturas; `PercepcionesDetalle`/`DeduccionesDetalle`/`OtrosPagosDetalle`/`IncapacidadesDetalle` en Nómina. Internos: NO van al Excel ni al visor en F2.6; la columna plana "Conceptos" se conserva | 2026-07-04 | Era EL bloqueo que detuvo F2.6: capturar en una forma que F4 no obligue a rehacer. Con nombres oficiales, el mapeo dict→columnas/extras de F4 es mecánico y sin re-parseo de XMLs; el fix multi-alumno IEDU cae solo (findall por concepto). Dueño ya había confirmado capturar en memoria ahora, no posponer |
| D26 | "Total Sueldos" de Nómina: **AMBAS** — se agrega el campo oficial `Percepciones@TotalSueldos` como columna nueva Y la columna actual se renombra a "Total Percepciones" (su contenido real) | 2026-07-04 | La etiqueta actual miente a un contador (incluye indemnizaciones/jubilaciones). Capturar ambos evita perder el dato existente y agrega el preciso. Decisión del dueño |
| D27 | Bug estructural de Pagos corregido en el mismo paso que el typo (no se pausó para volver a Fable): cada bucle de `PAGO_FIELDS_TO_EXTRACT` ahora filtra por el `xpath` declarado en su tupla, en vez de procesar la lista completa contra cualquier nodo | 2026-07-04 | Hallado al escribir la prueba del typo: `MontoTotalPagos` y 10 columnas de Totales SIEMPRE salían `None`, y "Version Pago" nunca se leía. Es un bug inequívoco (sin ambigüedad de diseño) descubierto en el mismo archivo que ya se estaba tocando — el dueño autorizó corregirlo de inmediato dado que el proyecto está en etapa temprana, en vez de regresar a auditoría |
| D28 | Filtro de Facturas ampliado a `UsoCFDI` y `Metodo de Pago` (ambos ya eran columnas visibles desde D18, solo faltaba poder buscarlos) — hecho directo por Sonnet, sin pasar por Fable/Opus | 2026-07-05 | Ajuste trivial explícitamente autorizado por el dueño ("no need of fable or opus to add this"). Es exactamente el caso previsto en D15 ("dejarlo abierto por si más adelante hace falta un campo"). NO se agregó a Nómina/Pagos porque esos campos no son columnas visibles ahí — repetiría el error de D17 (buscable pero invisible) |
| D29 | Fase **F2.7** aprobada tras evaluación crítica (§16): exportación filtrada "espejo del visor" — cada hoja según SU propio filtro de pestaña; botón NUEVO separado (el actual jamás cambia de comportamiento); sufijo derivado del query sanitizado con fallback `_Filtrado`; sin leyenda dentro de las hojas (rompería INDEX/MATCH al mover encabezados de la fila 1); fidelidad exportado≡visible como criterio duro | 2026-07-05 | El dueño pidió veredicto de contador senior + UX antes de aceptar la idea. Veredicto: construir — el trabajo contable es por subconjuntos y el visor hoy filtra en pantalla pero exporta TODO (promesa rota/violación WYSIWYG); riesgo técnico bajo porque `filter_records` ya existe pura y probada; el riesgo real es contable (parcial confundido con completo) y se mitiga con el nombre derivado del filtro. "Espejo del visor" y "sufijo derivado" fueron elecciones explícitas del dueño entre opciones presentadas |
| D30 | Fase **F2.8** "Papel de trabajo fiscal" aprobada tras entrevista de 3 rondas (§17): exclusiva de la edición **Pro**; escalera de reportes por edición (Lite = Excel actual sin PT; Pro = PT de IVA por flujo; Top = análisis ISR/IVA + flujo PF-RESICO vs PM devengado + cotejo IMSS, solo ESBOZADOS). Gate provisional: UN punto de decisión mínimo sobre el mecanismo de configuración existente (F2.5), default = TODO habilitado; en F9 `editions.py` sustituye la bandera sin mover la lógica del reporte. **Matiza D10, no la contradice**: no hay sistema de licencias antes de F9 | 2026-07-05 | El dueño definió el PT como diferenciador comercial de Pro, pero pruebas/beta deben ver todo (no hay licencia real corriendo). Construir el candado completo hoy violaría D10; no dejar NINGUNA costura obligaría a rediseñar en F9 |
| D31 | Ancla temporal del PT (orientado a IVA por flujo): **PUE → mes de emisión** (se presume pagado); **PPD → mes de `FechaPago` de cada REP** que lo paga (cada parcialidad `ImpPagado` suma a SU mes); PPD sin REP dentro del lote = **"PROVISIONADO"** visible, no deducible/acreditable aún. Lote **multi-mes elegido por el usuario** (opción (a)): procesa la carpeta que abarque el periodo — mes suelto, varios o ejercicio completo para el cierre anual. El histórico automático inter-lote llega con F4 (`pagos_doctos.id_documento`, §14.2). Moneda: todo se normaliza a MXN vía `Tipo De Cambio` (ya capturado; REP usa `TipoCambioP`/`EquivalenciaDR`) | 2026-07-05 | LIVA 5-III (acreditamiento cuando el IVA fue efectivamente pagado en el mes) y LIVA 1o.-B (efectivamente cobrado), verificados TEXTUALMENTE en los .md de fundamentos legales. El dueño entendió y aceptó el límite del lote: el usuario controla el periodo y F4 lo madura |
| D32 | Clasificación **bancarizado = columna oficial "Bancarizado" de c_FormaPago** (`docs/catalogos_filtrados.md`): Sí = 02, 03, 04, 05, 06, 28, 29; No = 01 y resto; **99 "Por definir" = Opcional → estatus "indeterminado"** (en PPD el 99 es legítimo — la forma real la da `FormaDePagoP` del REP y por ELLA se clasifica; PUE con 99 = anomalía marcable). Reglas de deducibilidad verificadas textualmente: **>$2,000 no bancarizado → no deducible** (LISR 27-III PM / 147-IV PF); **combustible no bancarizado → no deducible sin importar monto** + el comprobante debe traer permiso vigente de Ley de Hidrocarburos (27-III párr. 2, DOF 12-11-2021); combustible/colegiaturas se identifican POR CONCEPTO vía `ClaveProdServ` familias 1510/8612 (`ConceptosDetalle` de F2.6). Nota: 06 "Dinero electrónico" es bancarizado por catálogo aunque el 27-III no lo lista textual | 2026-07-05 | Regla anti-alucinación §13.1 extendida al dominio fiscal: TODA regla del PT quedó anclada a texto legal en `D:\repos\papel-trabajo_contable-fiscal\sources\fundamentos-legales\` o a catálogo oficial en `docs/`. La corazonada del dueño sobre 99/dinero electrónico/tarjeta de servicios resultó CORRECTA contra el catálogo |
| D33 | Notas de crédito en el PT: solo CFDI tipo **E con `TipoRelacion` 01 o 03 y UUID relacionado explícito**; el neteo ocurre en el **mes del evento** (LIVA Art. 7: quien recibe el descuento/devolución disminuye su acreditable en el mes en que se dé el supuesto, con restitución expresa del IVA), NO en el mes de la factura origen. Tipo E con `TipoRelacion` 07 (aplicación de anticipos) se EXCLUYE del neteo normal y se lista aparte. La columna "NC" es VISIBLE en el resumen — nunca resta silenciosa | 2026-07-05 | El dueño pidió explícitamente "¿qué dice la ley?" en vez de su intuición; LIVA 7 verificado textual. Excluir el 07 evita doble-neteo con la mecánica de anticipos |
| D34 | PT con **ambas direcciones en hojas SEPARADAS** (jerarquía D21 intacta): Recibidas = análisis de egresos/deducibilidad; Emitidas = ingresos + cuentas por cobrar por cliente ("facturado vs cobrado vs saldo por RFC receptor"). Columna manual **"Conciliado banco"** (el usuario marca ✓ contra su estado de cuenta) con sumas vivas tipo SUMAR.SI → **las hojas PT llevan FÓRMULAS reales de Excel, no valores congelados** (capacidad nueva del exporter, alcance de construcción F2.8). El PT NO sale en la exportación filtrada de F2.7 (un resumen fiscal sobre datos filtrados sería un resumen mentiroso); solo en la exportación completa | 2026-07-05 | "De nada sirve facturar 10M si solo has cobrado 100k" (dueño). La conciliación automática sigue FUERA (D22) — la marca manual es la respuesta práctica al hecho de que el CFDI declara y solo el banco confirma |
| D35 | Cotejo IMSS = **proyección estimada, edición Top, solo ESBOZADA** (diseño fino en sesión futura): base CFDI (SBC, SDI, días pagados, incapacidades — ya capturados en F2.6) + insumos capturados por el usuario (UMA vigente, prima de riesgo de trabajo, que NO existen en el CFDI ni en la ley como valores). `LSS.md` ya está en fundamentos legales para citar las fórmulas de cuotas al diseñarlo. **NO sustituye al SUA** y el disclaimer lo dirá. Disclaimer general del PT (hoja Fundamentos): "proyección estimada con base en CFDI; no constituye cálculo de impuestos; el uso y criterio son responsabilidad del usuario/contador" | 2026-07-05 | Veredicto honesto pactado con el dueño ("si no es viable, dilo"): el cálculo exacto es SUA; el cotejo estimado sí aporta y cabe en el molde Top con el deslinde que el propio dueño redactó |

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
7. **REGLA DE RESPALDO (D20):** antes de cualquier ola de cambios a los
   parsers (`xml_parser_*.py`, `pagos_parser_*.py`), verifica que el árbol
   git esté limpio, la suite verde, y que exista un tag de respaldo del
   estado funcional (patrón `vX.Y.Z-estable`). Si no existe, créalo antes de
   tocar el primer archivo.
8. **REGLA ANTI-ALUCINACIÓN DE ESQUEMAS (§13.1):** los campos del SAT se
   auditan/agregan SOLO contra XSD o catálogos oficiales presentes en
   `docs/`. Si el documento no está, se le pide al dueño — NUNCA se inventa
   un campo de memoria de entrenamiento.

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
5. **Iconografía de la app (registrado 2026-07-12, al construir B3):** hoy la
   UI es solo texto. Falta un set de íconos coherente (Bóveda, Cargar,
   Descargar, Recargar, año/mes, Emitidas/Recibidas). Recomendación técnica
   registrada: usar un set libre de licencia limpia para empaque LGPL —
   **Lucide (ISC)** o **Material Symbols (Apache-2.0)**, ambos SVG monolínea
   theme-ables vía `currentColor` (sirven en claro/oscuro, Sec.5.4)— y reservar
   SVGs hechos a mano solo para la marca propia (logo CFDI/Bóveda). Evitar packs
   de licencia dudosa. Tarea de pulido, NO bloquea funcionalidad. Su propia
   sesión cuando el dueño lo pida.
6. **Descarga SAT + "Reports/árbol global" (routed a Fable, 2026-07-12):** al
   diseñar B3 el dueño pidió un flujo **Descargar (Descargar del SAT →
   auto-categorizar en `BovedaCFDI/{RFC}/…`)** y una vista **"Reports" con el
   árbol de TODOS los RFCs de la bóveda**. Eso es arquitectura de shell/
   dashboard (Sec.5.3) + depende de F6 (CIEC/e.firma). Decisión del dueño:
   **esa parte arquitectónica se entrega a Fable** (prompt maestro vía
   `fable-session-builder`) y luego se vuelve a Sonnet/Opus para construir. En
   B3 solo quedó **el botón "Descargar…" deshabilitado (gris)** como placeholder
   de F6, más el menú **Bóveda → "Descargar del SAT…"** también deshabilitado.

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

### Cierre de F2.5 — CONFIRMADO por el dueño (2026-07-04, 3 rondas de prueba real)
- [x] Visor aparece tras procesar (antes de cualquier Excel); filtro por
  concepto ("energía"→CFE, "Cemento", "Mortero") y por monto funcionando;
  totales correctos. Palabras del dueño: "mind-blowing".
- [x] Paleta "Office/Excel Dark" (D16) confirmada visualmente ("it is looking
  good, very good"); numeración de filas 1..N tras ordenar corregida y
  confirmada.
- [x] Ventana vuelve a encogerse (fix del `totals_label` sin word wrap) —
  confirmado: "Perfecto, ya funciona".
- [x] Siguiente fase decidida: **F2.6** (captura de campos faltantes),
  bloqueada hasta recibir los XSD del SAT (ver §13). F3/F4 siguen después.
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

**Pregunta abierta — RESUELTA el mismo día (ver D18):** columnas visibles →
default curado ampliado YA + selector configurable en F3.

## 13. Auditoría de completitud de campos (2026-07-04) — F2.6

Auditoría solicitada por el dueño: verificar si los parsers extraen TODO lo
que el esquema oficial del SAT define, no solo lo que el visor muestra (eso ya
se curó en D18).

### 13.1 Método (regla anti-alucinación)

- **Núcleo CFDI 4.0: AUDITADO** contra `docs/cfdv40.xsd` — el XSD **oficial**
  del SAT que ya vivía en el repo. Se extrajo programáticamente cada
  elemento/atributo declarado y se comparó contra los 98 campos que un
  registro real captura hoy. Cero campos inventados de memoria.
- **Complementos (Nómina 1.2, Pagos 2.0, IEDU, ImpLocal): EN ESPERA.** Sus
  XSD NO están en el repo y NO se auditaron de memoria a propósito — el
  conocimiento de entrenamiento de un modelo no es fuente autoritativa para
  esquemas fiscales. El dueño subirá los archivos (ver 13.4).

### 13.2 Hallazgos del núcleo CFDI 4.0

**Bien cubierto:** `Comprobante` 18/19 atributos, `Receptor` 7/7,
TimbreFiscalDigital completo, totales de impuestos con desglose por tasa.

**Faltantes confirmados (contra XSD oficial):**

| Campo | ¿Importa? | Nota |
|---|---|---|
| `InformacionGlobal` (Periodicidad/Meses/Año) | **ALTA** | Factura global de público en general (RFC XAXX010101000) — sin esto no se distingue de una factura normal. Gasolineras/tiendas la usan a diario |
| `CfdiRelacionados@TipoRelacion` | **ALTA** | Se captura el UUID relacionado pero NO el tipo (01 nota de crédito, 04 sustitución…). `constants.py:316` dice que se excluyó a propósito — motivo original desconocido; recuperar en F2.6 |
| `Concepto@CuentaPredial` | **MEDIA-ALTA** | Obligatoria para arrendamiento — relevante para deducción de rentas |
| `Concepto/InformacionAduanera@NumeroPedimento` | MEDIA | Importaciones |
| `Comprobante@Confirmacion` | BAJA | Confirmación de PAC para montos atípicos — raro |
| `Emisor@FacAtrAdquirente` | BAJA | Facturación por adquirente — raro |
| `ACuentaTerceros`, `Concepto/Parte` | BAJA | Casos raros |
| `RegimenFiscal Emisor` | (inconsistencia) | **SÍ se captura** pero NO está en las 62 columnas del Excel — arreglo barato en F2.6 |

**Hallazgo ESTRUCTURAL (el más importante):** el modelo actual es 1 fila =
1 CFDI y los conceptos se aplanan a un string (`Conceptos`). Por eso no existe
"Monto Colegiatura": no hay captura POR-CONCEPTO de nada — `ClaveProdServ`,
`Cantidad`, `ClaveUnidad`, `ValorUnitario`, `Importe`, `Descuento` y
`ObjetoImp` por línea se leen (algunos) y se descartan. El caso IEDU del dueño
es un síntoma de esta limitación general. La casa natural de la solución ya
estaba decidida sin saberlo: la **tabla normalizada de conceptos de F4** (D9).
F2.6 DISEÑA esa captura; F4 la almacena plenamente. Bonus: guardar
`ClaveProdServ` por concepto convierte la detección de combustible de
heurística débil a casi determinista (ver §5.5.1).

### 13.3 Alcance decidido (D19)

- **SE AUDITA:** los 4 complementos que la app ya usa — Nómina 1.2,
  Pagos 2.0, IEDU, Impuestos Locales.
- **FUERA deliberadamente** (análisis costo/beneficio del dueño, compartido
  por el auditor): **Carta Porte** (nicho de transportistas con ERP propio),
  **Comercio Exterior cce20** (sin clientes importadores/exportadores hoy) y
  **auditoría del parser 3.3** (solo archivos históricos pre-2022; si llega
  una auditoría fiscal de 5/10 años, se decide entonces). NO se prepara nada
  anticipadamente: la arquitectura de aislamiento por versión garantiza que
  agregar un complemento después es costo acotado (un módulo nuevo + una rama
  de despacho), y los modelos futuros lo harán más barato. **Disparador
  documentado:** primer cliente real que lo necesite.

### 13.4 Archivos que el dueño subirá a `docs/sat/` (BLOQUEAN F2.6)

| # | Archivo | Para qué |
|---|---|---|
| 1 | `nomina12.xsd` | Auditar los ~40 campos de Nómina 1.2 (rev. C) |
| 2 | `pagos20.xsd` | Auditar las 115 columnas de Pagos 2.0 |
| 3 | `iedu.xsd` | Cerrar formalmente el caso colegiaturas |
| 4 | `implocal.xsd` | Impuestos Locales (ISH etc.) |
| 5 | `catCFDI.xls`/`.xlsx` | Catálogos CFDI 4.0 — en especial `c_ClaveProdServ` (lista oficial completa de claves de combustible y de servicios educativos) |
| opc. | Guía de llenado Anexo 20 (PDF) | Contexto útil, no indispensable |

Fuente: portal del SAT, sección Anexo 20 (esquemas y catálogos). Al recibirse,
se convertirán a Markdown de referencia y se ejecutará la auditoría de
complementos con el mismo método de 13.1. **F2.6 no arranca sin esto.**

> **✅ RECIBIDOS los 5 archivos (2026-07-04, mismo día).** El dueño los subió a
> `docs/` (junto al cfdv40.xsd existente, no en subcarpeta — aceptado así).
> Notas de los archivos: `iedu.xsd` venía con el esquema DUPLICADO (artefacto
> de copy-paste del navegador) y un `&` sin escapar en el patrón del RFC (así
> lo distribuye el SAT) — ambos se manejaron en memoria al parsear, el archivo
> NO se modificó. `catCFDI.xsd` (5.5 MB): trae 21 catálogos incluido
> `c_ClaveProdServ` completo (52,747 claves) pero SIN descripciones — sirve
> para validar existencia y extraer familias completas; si algún día se
> necesitan las descripciones individuales, se pediría el `catCFDI.xls`
> (opcional, hoy no bloquea nada).
> **Referencia generada:** `docs/sat-esquemas-referencia.md` — estructura
> completa de los 5 esquemas extraída PROGRAMÁTICAMENTE (no a mano), lista
> para que el constructor de F2.6 trabaje sin re-parsear XSDs.

### 13.5 Resultados de la auditoría de complementos (2026-07-04) — F2.6 DESBLOQUEADA

Auditados los 4 complementos contra sus XSD oficiales con el método 13.1:

**🐛 BUG REAL DE PRODUCCIÓN (Pagos 2.0):** `constants.py` extrae el atributo
`TotalTrasladadoBaseIVAExento`, pero el nombre oficial en `pagos20.xsd` es
`TotalTrasladosBaseIVAExento` ("Traslados", no "Trasladado"). El atributo mal
escrito JAMÁS coincide en un XML real → esa columna siempre sale 0.00 aunque
el comprobante traiga el dato. Corregir en F2.6 (una línea + prueba).

**🐛 CLAVE MUERTA (combustible):** de las 4 claves hardcodeadas en
`FUEL_PROD_SERV_CODES`, la `15101501` NO existe en el catálogo oficial. La
familia oficial 1510 (combustibles) tiene **35 claves** — el diesel
(`15101505`) y 30 más no están en la lista actual y hoy solo se detectan por
palabra clave. F2.6: reemplazar por las 35 oficiales (constante generada desde
el catálogo, ver referencia MD), manteniendo keywords como respaldo.

**⚠️ ETIQUETA ENGAÑOSA (Nómina):** la columna Excel "Total Sueldos" en
realidad contiene `Nomina@TotalPercepciones`. El atributo oficial
`Percepciones@TotalSueldos` es OTRA cosa (solo sueldos, sin indemnización ni
jubilación) y NO se captura. Para un contador esa etiqueta miente.
**RESUELTO (D26, 2026-07-04): AMBAS cosas** — se agrega el campo oficial
`Percepciones@TotalSueldos` como columna NUEVA, y la columna actual se
renombra a "Total Percepciones" para que diga la verdad. Nadie pierde el dato
que ya tenía.

**Faltantes por complemento:**

| Complemento | Estado | Faltantes |
|---|---|---|
| **Pagos 2.0** | ✅ Prácticamente completo | Solo el bug del typo (arriba). Columnas legacy de Pagos 1.0 (`TipoCambioDR`, `MetodoDePagoDR`) se conservan inofensivas |
| **IEDU** | ⚠️ Incompleto | Falta `autRVOE` [REQ] (autorización RVOE — parte del requisito de deducibilidad de colegiaturas) y `rfcPago` [opt] (RFC de quien paga — clave cuando paga un tercero). Además solo se captura el PRIMER `instEducativas` (`find`, no `findall`): factura con varios alumnos pierde a los demás |
| **ImpLocal** | ✅ Aceptable | Totales + ISH capturados. Se pierde el detalle por impuesto local individual distinto de ISH (nombre/tasa de cada uno se suma sin identificar) — MEDIA, mejora natural con la captura por-línea de F4 |
| **Nómina 1.2** | ⚠️ Varios huecos | Comentados a propósito en `constants.py` ("Not in Excel list"): `NumDiasPagados` [REQ], `TipoContrato` [REQ], `Banco`, `CuentaBancaria`. Nunca extraídos: `TipoRegimen` [REQ], `NumEmpleado` [REQ], `Departamento`, `Puesto`, `RiesgoPuesto`, `Sindicalizado`, `TipoJornada`, `SubContratacion`, `EntidadSNCF`, `Percepciones@TotalSueldos`/`TotalSeparacionIndemnizacion`/`TotalJubilacionPensionRetiro`, y TODO el detalle por línea (cada Percepción/Deducción/OtroPago con su Clave y Concepto, `HorasExtra`, `Incapacidades`, `SubsidioAlEmpleo@SubsidioCausado`, `JubilacionPensionRetiro`, `SeparacionIndemnizacion`) — el mismo patrón estructural del §13.2: los renglones se aplanan |

**Bonus para el futuro filtro de colegiaturas del dueño:** familia oficial
8612 (servicios educativos) = 15 claves, ya extraídas en la referencia MD —
detectar colegiaturas por `ClaveProdServ` será exacto cuando exista la
captura por-concepto.

## 14. Diseño técnico de F4 — Bóveda SQLite ELÁSTICA (2026-07-04)

Diseñado ANTES de construir F2.6 a petición del dueño: la forma en que F2.6
captura el detalle por-concepto depende de cómo F4 guardará y evolucionará el
esquema. Este diseño responde su pregunta explícita: *"¿el día que salga una
nueva versión de CFDI o un complemento nuevo, se puede agregar sin romper
nada?"* — **Sí, con el diseño de abajo.**

### 14.1 SQLite híbrido, NO MongoDB (D24)

El dueño (con experiencia previa en MongoDB) preguntó si convenía un almacén
tipo documento. **Veredicto: NO**, por razones de fondo, no de gusto:

1. **Privacidad:** Mongo práctico = Atlas (nube) → datos fiscales de clientes
   en un tercero. Contradice la propuesta de confianza de la app y la misma
   lógica de D9 (embeddings) y la regla e.firma. Mongo local = un SERVIDOR
   aparte imposible de empaquetar razonablemente con PyInstaller para
   contadores no técnicos.
2. **Capacidad:** free tier de Atlas (512 MB) vs. objetivo de 200,000+ XMLs —
   "se come el proyecto" (palabras del dueño).
3. **Cero dependencias:** SQLite viene en la stdlib de Python, es UN archivo
   en `Documents\CFDI-Processor\` (respaldable copiándolo), y su modo híbrido
   relacional+JSON da la elasticidad tipo-Mongo que se busca CON poder SQL
   donde importa (filtros/sumas/joins de F5).

**Entorno verificado en la máquina del dueño (no asumido):** SQLite 3.50.4
vía `sqlite3` de Python 3.14. Probado en vivo: funciones JSON
(`json_extract`), `ALTER TABLE ADD COLUMN` no destructivo (filas viejas
intactas), índices sobre expresiones JSON, `PRAGMA user_version`. Mínimos
requeridos por este diseño: funciones JSON integradas (estándar desde SQLite
3.38, 2022) e índices de expresión (desde 3.9, 2015) — cualquier Python
3.10+ moderno los cumple; aún así, la bóveda hará un **check de versión al
inicializar** y se negará con mensaje claro si el runtime fuera anciano.

### 14.2 Esquema conceptual (DDL final se escribe en F4)

Regla de reparto: va a **columna relacional** lo que (a) es común a todas las
versiones CFDI conocidas Y (b) se filtra/agrupa/suma en F5 (RFC, dirección,
fechas, montos, claves). TODO lo demás nace en `extras` (JSON).

```
cfdi          1 fila por comprobante. PK: uuid (dedup natural).
              Relacional: version_cfdi, tipo, serie, folio, fecha_emision,
              fecha_timbrado, rfc_emisor, nombre_emisor, regimen_emisor,
              rfc_receptor, nombre_receptor, uso_cfdi, subtotal, descuento,
              total, moneda, tipo_cambio, forma_pago, metodo_pago,
              lugar_expedicion, direccion_doc ('EMITIDA'/'RECIBIDA' respecto
              al RFC dueño — jerarquía dura de D21), estado_sat (se llena en
              F7), archivo_xml, fecha_importacion,
              complementos (JSON: lista de nombres detectados),
              extras (JSON) ← todo lo no mapeado
conceptos     1 fila por línea de concepto. FK cfdi_uuid + num_linea.
              Relacional: clave_prod_serv, no_identificacion, cantidad,
              clave_unidad, unidad, descripcion, valor_unitario, importe,
              descuento, objeto_imp, complemento_tipo (p.ej. 'iedu').
              JSON: complemento (autRVOE/CURP/nivel/rfcPago…), impuestos
              (traslados/retenciones de la línea), extras.
              → Aquí viven: colegiatura por monto, combustible por clave
                oficial, FTS5 de F5 sobre descripcion (D9).
nomina        1 fila por CFDI tipo N. Relacional: fechas de pago, num_dias,
              curp, nss, num_empleado, tipo_contrato, tipo_regimen, registro
              patronal, sbc, sdi, totales oficiales. JSON: percepciones,
              deducciones, otros_pagos, incapacidades (arrays), extras.
pagos         1 fila por nodo Pago (un CFDI-P puede traer varios). FK
              cfdi_uuid. Relacional: fecha_pago, forma, moneda, tipo_cambio,
              monto, num_operacion, cuentas bancarias. JSON: extras.
pagos_doctos  1 fila por DoctoRelacionado. FK al pago. Relacional:
              id_documento (=uuid de la factura pagada → habilita conciliar
              REP↔factura con un join), serie, folio, moneda_dr,
              equivalencia, num_parcialidad, imp_saldo_ant, imp_pagado,
              imp_saldo_insoluto, objeto_imp_dr. JSON: impuestos_dr, extras.
(versionado)  PRAGMA user_version = número de migración del esquema de la
              app + tabla schema_meta con el log de migraciones aplicadas.
```

### 14.3 Política de elasticidad (las 4 reglas)

1. **Campo nuevo nace en `extras` (JSON): cero migración.** El contrato del
   INSERT de la bóveda es: claves conocidas del dict del parser → columnas;
   TODO lo no mapeado → `extras` automáticamente. Un parser nuevo puede
   producir campos que la DB nunca ha visto y se guardan igual, día uno.
2. **Promoción de campos calientes:** si un campo de `extras` se vuelve
   consultable (filtros/reportes), se promueve: `ALTER TABLE ADD COLUMN` +
   backfill `UPDATE … SET col = json_extract(extras,'$.Campo')` + índice.
   Aditivo, no destructivo, filas viejas intactas (verificado en vivo).
3. **Migraciones numeradas y SOLO aditivas** (`user_version` N→N+1 al
   arrancar la app). Jamás DROP/renombrado en caliente: renombrar = columna
   nueva + backfill, la vieja se queda hasta una limpieza mayor programada.
4. **Respaldo automático del archivo .db ANTES de aplicar cualquier
   migración** (copia con sufijo de fecha — es un solo archivo, costo
   trivial). Consistente con la filosofía de respaldo del dueño (D20).

### 14.4 Flujo "SAT libera CFDI 4.1 / complemento nuevo" (paso a paso)

1. Tag git de respaldo (regla §8.7).
2. Nuevo `parsers/xml_parser_41.py` + UNA rama de despacho (regla intocable
   §2.1). Los parsers existentes NO se tocan.
3. El parser nuevo produce su dict con nombres oficiales del XSD. Al
   importar: campos que ya existen como columna → columna; campos nuevos →
   `extras`. **Cero ALTER TABLE, cero migración, cero riesgo el día uno.**
   Las filas viejas (4.0) conviven con las nuevas (4.1) — `version_cfdi`
   dice de cuál versión viene cada una.
4. Si un campo nuevo se vuelve importante para filtrar → promoción (regla
   14.3.2) cuando se necesite, no antes.
5. Complemento nuevo → su detalle entra a `conceptos.complemento`/`extras`;
   solo amerita tabla propia si su cardinalidad lo exige (como pagos_doctos).

**Respuesta directa a la pregunta del dueño: sí — versión o complemento nuevo
se agrega sin romper nada, sin migración destructiva, y sin tocar lo viejo.**

### 14.5 Contrato de captura para F2.6 (desbloquea la construcción)

Lo que el parser debe producir HOY para que F4 lo guarde mañana sin fricción
y sin re-abrir ningún XML:

- `data["ConceptosDetalle"]` = **lista de dicts Python nativos** — NO un
  string JSON pre-serializado (serializar es asunto del almacenamiento en F4;
  en memoria, visor y filtros futuros la consumen directa). Un dict por línea
  de concepto, **claves = nombres oficiales del XSD tal cual**:
  `ClaveProdServ, NoIdentificacion, Cantidad, ClaveUnidad, Unidad,
  Descripcion, ValorUnitario, Importe, Descuento, ObjetoImp`, más subdicts
  opcionales `Complemento` (p.ej. `{"tipo": "iedu", "autRVOE": …, "CURP": …,
  "nivelEducativo": …, "nombreAlumno": …, "rfcPago": …}`) e `Impuestos`
  (traslados/retenciones de esa línea). El fix multi-alumno IEDU (§13.5) cae
  solo con esto: `findall` por concepto, cada alumno en su línea.
- Mismo patrón en Nómina: `PercepcionesDetalle`, `DeduccionesDetalle`,
  `OtrosPagosDetalle`, `IncapacidadesDetalle` (listas de dicts, nombres
  oficiales del XSD de nomina12).
- Estos campos internos **NO van al Excel** (se excluyen como ya se excluye
  `CFDI_Type`) y **NO son columna del visor en F2.6**. La columna plana
  `Conceptos` (string concatenado) se CONSERVA tal cual para visor/filtro.
- Por qué nombres oficiales: el mapeo dict→columnas de F4 se vuelve mecánico
  y cualquier auditoría futura contra XSD sigue siendo trivialmente
  verificable (§8.8).

## 15. Resultado de F2.6 (construida 2026-07-04)

F2.6 se construyó completa siguiendo §13 (auditoría) y §14.5 (contrato de
captura), en pasos chicos con pruebas después de cada uno.

### 15.1 Bug estructural adicional encontrado (no estaba en la auditoría original)

Al escribir la prueba del typo de Pagos (una sola columna), se descubrió un
bug **más grande**: `PAGO_FIELDS_TO_EXTRACT` mezcla atributos de 3 niveles
distintos del XML (`pago20:Pagos`, `pago20:Totales`, `pago20:Pago`) en una
sola lista, pero cada bucle de extracción recorría la lista COMPLETA sin
filtrar por el `xpath` que cada tupla ya traía declarado. Consecuencia real:
**`MontoTotalPagos` y las 10 columnas de Totales SIEMPRE salían `None`**
(no solo la del typo), y `"Version Pago"` nunca se leía de ningún lado. La
auditoría de nombres contra XSD (§13.1) no lo detectó porque es un tipo de
revisión distinto — comparar nombres de atributos no es lo mismo que rastrear
si el valor sobrevive hasta el diccionario final. **Corregido** haciendo que
cada bucle (`pagos_complement`, `Totales`, `Pago`) filtre por su propio
`xpath` en vez de procesar la lista entera a ciegas — 4 pruebas nuevas en
`tests/test_pagos_parser.py` cubren el caso.

### 15.2 Cambios por complemento

- **Combustible:** `FUEL_PROD_SERV_CODES` reemplazado por las 35 claves
  oficiales de la familia 1510 (antes 4, una de ellas muerta). Se agregó
  `EDU_PROD_SERV_CODES` (15 claves, familia 8612) como bonus para detectar
  colegiaturas por clave — verificado con el fixture real de IEDU.
- **Núcleo CFDI 4.0:** `InformacionGlobal` (`Comprobante Global`,
  `Periodicidad Global`, `Meses Global`, `Año Global`), `CfdiRelacionados@TipoRelacion`
  (código crudo — sin descripción inventada, el XSD no la trae y el catálogo
  oficial resultó tener 9 códigos, no los 7 "recordados" de entrenamiento;
  confirma por qué la regla anti-alucinación importa), `RegimenFiscal Emisor`
  agregado a `INVOICE_COLUMN_ORDER` (ya se capturaba, nunca llegaba al Excel).
- **IEDU:** `autRVOE` y `RFC Pago Colegiatura` (`rfcPago`) agregados a las
  columnas planas de resumen (primer alumno, compatibilidad hacia atrás). El
  caso multi-alumno se resuelve completo vía `ConceptosDetalle` (cada alumno
  en su propio concepto, sin pérdida de datos).
- **Nómina:** columna renombrada `"Total Sueldos"` → `"Total Percepciones"`
  (contenido real sin cambios) + nueva `"Total Sueldos"` desde el campo
  oficial `Percepciones@TotalSueldos` (D26 — ambas cosas, dato viejo
  conservado). Agregados: `Num Dias Pagados`, `Tipo Contrato`, `Tipo Regimen`,
  `Num Empleado`, `Departamento`, `Puesto`, `Riesgo Puesto`, `Sindicalizado`,
  `Tipo Jornada`, `Total Separacion Indemnizacion`,
  `Total Jubilacion Pension Retiro`, y (casos raros, primer/único nodo)
  `EntidadSNCF`/`SubContratacion`.
- **Captura por-concepto (D25):** `ConceptosDetalle` (Facturas/Nómina) y
  `PercepcionesDetalle`/`DeduccionesDetalle`/`OtrosPagosDetalle`/
  `IncapacidadesDetalle` (Nómina) — listas de dicts con nombres oficiales del
  XSD, verificadas contra fixtures reales. Excluidas explícitamente del Excel
  vía `constants.INTERNAL_ONLY_FIELDS` (Nómina no reindexa a una lista fija de
  columnas — sin esta exclusión, habrían salido como texto de lista de Python
  en una celda).

### 15.3 Verificación

- **81 pruebas verdes** (66 previas + 15 nuevas de F2.6, incluyendo las 4 del
  bug estructural de Pagos).
- Lote completo de `XML-Test/` reprocesado: 13 archivos, 0 errores, Excel de
  70 columnas en Facturas (62+8) sin ninguna columna interna filtrada.
- E2E headless de la GUI (hilo real) confirmó que el visor de F2.5 sigue
  funcionando sin cambios tras estas modificaciones al parser.

### Pendiente para cerrar F2.6 al 100%
- [ ] Confirmación del dueño en máquina real (regla §8.4): reprocesar XMLs
  reales y revisar que el Excel de Facturas/Nómina se vea correcto con las
  columnas nuevas. (El dueño ya confirmó parcialmente: el caso de
  colegiaturas funcionó en su prueba del 2026-07-05.)
- [ ] Decidir con el dueño la siguiente fase: F3 (directorio de trabajo +
  auto-organización) o F4 (construir la bóveda SQLite, ya diseñada en §14).

## 16. Diseño de F2.7 — Exportación filtrada "espejo del visor" (2026-07-05)

Idea del dueño, evaluada críticamente ANTES de aceptarla (pidió veredicto de
contador senior + UX, no un sí automático). **Veredicto: SÍ se construye.**

### 16.1 Por qué existe (la evaluación)

- **Contable:** el trabajo real es por subconjuntos (cédula de colegiaturas
  D10, gastos de combustible, facturas de un proveedor, PPD pendientes). Hoy
  el visor filtra y recalcula totales en pantalla… y el botón de exportar
  entrega TODO — una promesa rota a medio camino. El subconjunto ES el
  entregable que un contador anexa a un papel de trabajo.
- **UX:** exportar-lo-que-ves es el comportamiento esperado de toda
  herramienta de datos; la anomalía es no tenerlo (principio WYSIWYG).
- **Estratégico (del dueño):** un usuario neófito de Excel (sin FILTER(),
  tablas dinámicas ni Power Query) resuelve todo desde la app — la vuelve
  indispensable, no solo un conversor.
- **Riesgo técnico BAJO:** `filter_records()` (la parte difícil) ya existe,
  es pura y tiene 15 pruebas. Lo nuevo es cableado + un botón. No toca hilos,
  máquina de estados ni parsers. El flujo actual de "Guardar Excel…" no
  cambia NI UNA LÍNEA.
- **Riesgo real (contable, mitigado por diseño):** un archivo parcial
  confundido con completo meses después. Mitigación: el nombre del archivo
  documenta el criterio del filtro (16.4).
- **Traslape con F5 asumido conscientemente:** F5 filtrará el historial
  (SQLite); esto filtra el lote actual. La costura "exportar subconjunto"
  construida aquí la reutiliza F5.

### 16.2 Alcance — "espejo del visor" (decisión del dueño)

El Excel exportado refleja EXACTAMENTE lo que el visor muestra: **cada hoja
sale según SU propio filtro** — pestañas con filtro activo salen recortadas,
pestañas sin filtro salen COMPLETAS. (Cada pestaña ya tiene su caja de
búsqueda independiente, así que Facturas puede salir filtrada por "tela"
mientras Nómina sale entera.) Degradación natural: sin ningún filtro activo,
el resultado es idéntico al export normal — por eso el botón se deshabilita
en ese caso (16.3).

### 16.3 UI

- **Botón NUEVO separado** ("Guardar filtrado…"), junto al "Guardar Excel…"
  actual. Habilitado SOLO cuando el estado es DONE **y** al menos una pestaña
  tiene filtro activo con >0 filas visibles.
- El botón actual NO cambia de comportamiento jamás (cambiar el significado
  de un botón según estado invisible es la clase de sorpresa que este
  proyecto mata desde el Bug 1).
- Reglas de oro §6.2 intactas: el diálogo de guardado nace del clic.
- Tras guardar, los botones "Abrir archivo"/"Abrir carpeta" apuntan al último
  archivo guardado, igual que hoy (sin lógica especial).

### 16.4 Nombre de archivo (decisión del dueño: derivado del filtro)

- Base: el MISMO nombre que hoy (`build_default_filename` sobre el lote
  completo — RFC/tipo/fecha no cambian por filtrar) + sufijo.
- **Sufijo derivado:** `_Filtrado_<texto>` donde `<texto>` es el query
  sanitizado: solo `[A-Za-z0-9_-]` (espacios→`_`, resto se elimina),
  operadores traducidos ANTES de sanitizar (`<`→`menor`, `>`→`mayor`,
  `<=`→`hasta`, `>=`→`desde`), truncado a ~30 caracteres.
  Ej.: `XAXX_Emitidas_2025_02_Filtrado_tela.xlsx`,
  `..._Filtrado_menor2000.xlsx`.
- **Fallbacks:** si hay filtros activos en VARIAS pestañas a la vez, o el
  texto queda vacío tras sanitizar → sufijo `_Filtrado` a secas.
- El diálogo de guardado propone este nombre y el usuario puede editarlo ahí
  mismo (gratis, es el diálogo estándar).
- **NO se agrega leyenda "filtros aplicados" DENTRO de las hojas:** movería
  los encabezados fuera de la fila 1 y rompería fórmulas INDEX/MATCH de los
  usuarios. El nombre del archivo es el único marcador de parcialidad.

### 16.5 Garantía de fidelidad (criterio de construcción duro)

La exportación DEBE usar la misma `filter_records()` con el mismo query y la
misma `TabConfig` que el visor — y una prueba debe afirmar que las filas
exportadas son IDÉNTICAS (misma cantidad y mismos registros) a las filas
visibles del proxy en ese momento. Si el visor y el archivo pueden divergir,
la función pierde su razón de ser.

### 16.6 Criterios de aceptación de F2.7

1. Con filtro "tela" en Facturas y Nómina sin filtro: el Excel trae Facturas
   recortada (solo coincidencias) y Nómina completa; el nombre termina en
   `_Filtrado_tela.xlsx`.
2. Con filtro `<2000`: sufijo `_Filtrado_menor2000.xlsx`.
3. Con filtros en dos pestañas: sufijo `_Filtrado.xlsx`.
4. Sin ningún filtro activo: el botón "Guardar filtrado…" está deshabilitado.
5. El botón "Guardar Excel…" actual se comporta EXACTAMENTE igual que antes
   (prueba de regresión).
6. Prueba de fidelidad de 16.5 en verde.
7. Suite completa verde + confirmación del dueño en máquina real (§8.4).

## 17. Diseño de F2.8 — Reporte fiscal "Papel de trabajo" (edición Pro) (2026-07-05)

Diseñado por entrevista de 3 rondas con el dueño + verificación **con ley en
mano**: todas las reglas fiscales se anclaron a texto legal en
`D:\repos\papel-trabajo_contable-fiscal\sources\fundamentos-legales\` (LISR,
LIVA, CFF, LIEPS, reglamentos, RMF 2026, LSS) o a catálogo oficial en
`docs/catalogos_filtrados.md`. La regla anti-alucinación §13.1 queda
EXTENDIDA al dominio fiscal/contable: ningún artículo se cita de memoria; lo
no verificado se marca "POR UBICAR". Decisiones: D30–D35.

### 17.1 Objetivo (una frase)

Convertir el lote procesado en un papel de trabajo mensual de IVA por flujo
de efectivo — qué está efectivamente pagado/cobrado, qué es
deducible/acreditable, qué queda provisionado — por mes y año, sin que el
contador arme nada a mano.

### 17.2 Reglas de negocio confirmadas (cada una con su fuente)

| # | Regla | Fuente (estado) |
|---|---|---|
| R1 | Pagos >$2,000 deben ser bancarizados para deducirse | LISR 27-III (PM) y 147-IV (PF) — **texto verificado** |
| R2 | Combustibles: bancarizado SIEMPRE, sin importar monto; el CFDI debe traer permiso vigente de Ley de Hidrocarburos | LISR 27-III párr. 2 (DOF 12-11-2021) — **texto verificado** |
| R3 | IVA acreditable solo cuando fue efectivamente pagado en el mes | LIVA 5-III — **texto verificado** |
| R4 | "Efectivamente cobrado/pagado": anticipos cuentan; cheque hasta su cobro; cualquier extinción de obligaciones | LIVA 1o.-B — **texto verificado** |
| R5 | Devoluciones/descuentos/bonificaciones (NC) se netean en el MES en que ocurren, con restitución expresa del IVA | LIVA 7 — **texto verificado** |
| R6 | Bancarizado se clasifica por la columna oficial del catálogo: Sí = 02,03,04,05,06,28,29; No = 01 y resto; 99 = Opcional/indeterminado | `docs/catalogos_filtrados.md` (c_FormaPago) — **verificado** |
| R7 | PPD se considera pagado solo con su REP; el mes lo da `FechaPago`; la forma de pago real es `FormaDePagoP` del REP | Mecánica CFDI/Anexo 20; regla RMF del plazo del REP **POR UBICAR** en RMF_2026 (ya en fundamentos) al redactar la hoja |
| R8 | Combustible y colegiaturas se identifican POR CONCEPTO vía `ClaveProdServ` (familias 1510 / 8612) | Catálogo + `ConceptosDetalle` (F2.6, D25) — **verificado** |

Notas de borde: (a) 06 "Dinero electrónico" es bancarizado por catálogo
aunque LISR 27-III no lo nombra textual — se clasifica por catálogo, con nota
en la hoja Fundamentos; (b) FormaPago 99 es legítimo en PPD (la forma real
llega en el REP); en PUE es anomalía marcable, no error; (c) sigue vigente
D22: el CFDI declara, solo el banco confirma — la columna "Conciliado banco"
(17.4) es la respuesta práctica, manual a propósito.

### 17.3 Ancla temporal y alcance del lote (D31)

- **PUE** → mes de su fecha de emisión (se presume pagado).
- **PPD** → mes de `FechaPago` de cada REP; cada parcialidad (`ImpPagado`)
  suma a SU mes; `NumParcialidad`/`ImpSaldoInsoluto` ya se capturan y
  permiten mostrar saldo restante por factura.
- **PPD sin REP en el lote** → fila "PROVISIONADO — no deducible/acreditable
  aún": visible, jamás desaparece en silencio.
- El **usuario elige el periodo procesando la carpeta que lo abarque** (un
  mes, varios, o el ejercicio completo para el cierre anual — donde el cruce
  PPD↔REP queda completo). El histórico automático entre lotes llega con F4.
- **Moneda:** todo importe se normaliza a MXN (importe × `Tipo De Cambio`,
  columna ya capturada con default 1.0; en REPs, `TipoCambioP`/`EquivalenciaDR`).

### 17.4 Estructura de hojas (mismo archivo Excel, al final; D34)

Pro — lo que F2.8 construye:

1. **PT-Recibidas (resumen)** — una fila por mes/año con columnas: PUE
   bancarizado; PUE efectivo deducible (≤ $2,000); PUE efectivo NO deducible
   (> $2,000); Combustible no deducible (efectivo, cualquier monto); PPD
   facturado; PPD pagado (vía REP del mes); PPD provisionado; NC recibidas
   (netean, R5); Subtotal / Descuento / IVA / Total netos; IVA acreditable
   estimado del mes.
2. **PT-Recibidas (detalle)** — una fila por CFDI recibido: datos base +
   FormaPago efectiva (de la factura, o del REP si es PPD) + mes asignado +
   **ESTATUS con formato condicional**: verde = deducible; rojo = efectivo
   > $2,000; rojo = combustible en efectivo; ámbar = PPD provisionado;
   ámbar = 99 indeterminado. Más la columna manual **"Conciliado banco"**
   (el usuario marca ✓ contra su estado de cuenta) cuyas sumas usan fórmulas
   vivas (SUMAR.SI) — **las hojas PT llevan fórmulas reales de Excel, no
   valores congelados** (capacidad nueva del exporter; alcance de F2.8).
3. **PT-Emitidas (resumen)** — por mes: facturado PUE/PPD, cobrado vía REP,
   por cobrar, NC emitidas, IVA trasladado efectivamente cobrado.
4. **PT-Emitidas (por cliente)** — facturado vs cobrado vs saldo por RFC
   receptor, ordenado por saldo ("empresa sutanita no me ha pagado").
5. **Fundamentos** — citas legales de 17.2 + disclaimer: "proyección estimada
   con base en CFDI; no constituye cálculo de impuestos; el uso y criterio
   son responsabilidad del usuario/contador".

Emitidas y Recibidas JAMÁS se mezclan en una misma hoja (D21). Los
encabezados de TODAS las hojas PT van en fila 1 (compatibilidad INDEX/MATCH,
misma razón que 16.4).

Top — solo ESBOZO (diseño fino en sesión futura, D35): "Análisis IVA"
(acreditable vs trasladado por flujo), "Análisis ISR" (PM devengado /
PF-RESICO flujo), "Cotejo IMSS" (proyección estimada: base CFDI + UMA y
prima de riesgo capturadas por el usuario; LSS.md ya en fundamentos; NO
sustituye SUA).

### 17.5 Fórmulas conceptuales (español llano — el constructor las traduce)

- PUE efectivo no deducible (mes M) = Σ Total de CFDI tipo I recibidos con
  MetodoPago = PUE y FormaPago = 01 y Total > 2000 y mes(emisión) = M. [R1]
- Combustible no deducible (M) = Σ Importe de CONCEPTOS con ClaveProdServ en
  familia 1510 cuando la FormaPago efectiva = 01, sin umbral. [R2, R8]
- PPD pagado (M) = Σ ImpPagado de DoctoRelacionado cuyos REP tengan FechaPago
  en M, casados por IdDocumento = UUID de la factura PPD del lote. [R7]
- NC aplicadas (M) = Σ Total de CFDI tipo E con TipoRelacion 01 o 03 y UUID
  relacionado presente, asignadas al mes del evento; tipo E con TipoRelacion
  07 (anticipos) se lista aparte, fuera del neteo. [R5, D33]
- IVA acreditable estimado (M) = IVA de PUE deducibles de M + IVA de los
  ImpPagado de REPs de M (ImpuestosDR) − IVA restituido por NC de M. [R3, R5]
- Suma conciliada = SUMAR.SI(columna de marca, "✓", columna de importe). [D34]

### 17.6 Ediciones y gate provisional (D30)

Lite = Excel actual sin PT · Pro = hojas PT de este diseño · Top = análisis
ISR/IVA/flujo + cotejo IMSS (nombre comercial pendiente). Desde F2.8 existe
UN punto de decisión mínimo (bandera sobre el mecanismo de configuración de
F2.5) con default = TODO habilitado: pruebas y beta ven todo. En F9,
`editions.py` sustituye la bandera sin mover la lógica del reporte. Cero
validación de licencias antes de F9.

### 17.7 Preguntas abiertas (confirmar con el dueño al construir)

1. Nombre comercial de la edición Top.
2. Regla RMF vigente del plazo de emisión del REP: ubicarla y citarla desde
   `RMF_2026-DOF-28122025.md` (ya en fundamentos) — NO citar de memoria.
3. Facturas globales (`InformacionGlobal`): ¿su Periodicidad/Meses/Año
   sustituyen al mes de emisión como ancla en PT-Emitidas?
4. Umbral $2,000: el texto legal dice "pagos cuyo monto exceda de $2,000.00"
   — confirmar criterio práctico (default propuesto: monto total pagado, IVA
   incluido).
5. Discrepancia menor detectada: el catálogo XLS vigente trae 7 códigos de
   `TipoRelacion`; el `catCFDI.xsd` enumeraba 9 (§15.2). Para el PT solo
   importan 01/03/07; verificar el resto solo si algún día se usan.

### 17.8 Lo que F2.8 NO cubre (para que el constructor no invente alcance)

- Nombres de archivos/clases/funciones Python: los decide la construcción.
- Conciliación bancaria automática (D22) — la marca ✓ es manual a propósito.
- Cálculo real/definitivo de impuestos: TODO es proyección estimada.
- Las hojas Top: solo esbozo; su diseño fino es otra sesión de análisis.
- Estatus SAT de los CFDI (vigente/cancelado) — eso es F7.
- Persistencia/histórico entre lotes — eso es F4.
- El export filtrado (F2.7) NO incluye hojas PT (D34); F2.7 se construye
  ANTES y F2.8 no la modifica.

### 17.9 Criterios de aceptación de F2.8

1. Lote multi-mes real: el resumen mensual de PT-Recibidas cuadra contra las
   hojas Invoices/Pagos existentes (mismas fuentes, sumas consistentes).
2. Un PPD con REP en el lote aparece pagado en el mes del REP; sin REP,
   aparece PROVISIONADO.
3. Un concepto de combustible (familia 1510) pagado con FormaPago 01 sale
   marcado NO deducible aunque valga $500.
4. Un CFDI de $2,500 con FormaPago 01 sale NO deducible; el mismo con 03
   sale deducible.
5. Una NC (tipo E, TipoRelacion 01, UUID relacionado) neta en su mes y es
   visible como columna propia.
6. La columna "Conciliado banco" acepta marcas del usuario y las sumas
   conciliadas recalculan EN Excel (fórmulas vivas).
7. Con la bandera de edición en "Lite", el Excel sale SIN hojas PT y es
   idéntico al actual (prueba de regresión); default = con PT.
8. Suite completa verde + confirmación del dueño en máquina real (§8.4).
