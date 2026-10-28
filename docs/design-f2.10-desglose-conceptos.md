# Diseño F2.10 — Reporte "Desglose de conceptos" (monederos Edenred + cualquier proveedor)

> Fecha: 2026-10-27
> Origen: petición del dueño. Las facturas de Edenred (`ASE930924SS7`) de
> gasolina no aparecen como gasolina en la app. Se pide un reporte que abra
> el detalle de lo que trae cada XML, por XML, mes, ejercicio y proveedor.
> También debe servir para Walmart, Home Depot y cualquier factura con muchos
> conceptos.
> Diseño: Opus. Constructor: Sonnet. Este documento NO contiene código, solo
> decisiones de arquitectura. Gobernanza ROADMAP §8: D11 (no quitar nada que
> funcione sin preguntar) y D20 (tag git ANTES de tocar el parser).

---

## 1. Hallazgo con XML reales (no hipótesis)

Se analizaron 5 XML reales de Edenred del receptor `GOOH841231EPA`. Edenred
emite **tres familias** de CFDI y solo una lleva gasolina:

| Serie | Qué es | Concepto CFDI (lo único que hoy lee la app) | Dónde está el dato real |
|---|---|---|---|
| **TCGE** | Estado de cuenta de **combustible** (monedero) | 1 línea: `84141602` / `E48` "COMISION SOBRE PEDIDOS" ($930 + IVA) | **Complemento `ecc12:EstadoDeCuentaCombustible` v1.2**: una línea por carga |
| TCTL | Telepeaje (casetas) | `95111603` **o** `84141602` / `E54` "VIAJE" "MOVIMIENTOS TELEPEAJE", Cantidad = nº de cruces | No hay detalle por caseta en el XML |
| TCTL | Etiqueta TAG | `84141602` "COBRO ETIQUETA DE PRESENCIA T", Descuento 100%, Total 0.00 | — |

Números verificados por script sobre los XML:

| UUID | CFDI Total | Complemento: líneas · litros · Importe · IVA · Total | ¿Cuadra con lo declarado? |
|---|---|---|---|
| `3358E192…` (jun-2026) | $1,078.80 | 33 cargas · 1,127.97 L · $24,393.77 · $3,791.92 · **$28,185.69** | Sí, al centavo |
| `46613d69…` (ago-2026) | $1,044.00 | 37 cargas · 1,603.79 L · $35,005.60 · $5,441.49 · **$40,447.09** | Sí, al centavo |

**Consecuencia:** hoy la app ve una comisión de ~$1,000 donde en realidad hay
~$28,000 a $40,000 al mes de gasolina con su IVA. Esto pasa porque ningún
parser lee `ecc12` (no existe ni una mención en `src/`). Por eso:

1. La columna `Combustible` dice "No": `84141602`/`E48` no es de la familia
   1510 (R8). Es lo correcto para la comisión, pero esconde la gasolina.
2. **PT-Recibidas (F2.8) no ve esa gasolina ni su IVA.** Es un hueco fiscal
   real. Por decisión del dueño (P3) se cierra en esta fase, en la etapa 4
   (§8), con el IVA como protagonista.

Datos de cada línea del complemento (nombres oficiales tal cual, D25):
`Identificador` (número de tarjeta, 5 tarjetas distintas por estado de
cuenta), `Rfc` (gasolinera), `ClaveEstacion`, `TipoCombustible`,
`NombreCombustible`, `FolioOperacion`, `Fecha` (de la carga), `Cantidad`
(litros), `Unidad`, `ValorUnitario`, `Importe` y `Traslados/Traslado`
(Impuesto="IVA", TasaOCuota, Importe). El encabezado trae `Version`,
`TipoOperacion`, `NumeroDeCuenta`, `SubTotal` y `Total`.

Trampa observada: `NombreCombustible` depende de la marca. El mismo
`TipoCombustible="1"` aparece como "Magna" y como "BP REGU". **Se agrupa por
`TipoCombustible`** y el nombre solo se muestra. Otra trampa: el telepeaje
usa dos `ClaveProdServ` distintas según el mes, así que clasificar Edenred
solo por clave falla.

---

## 2. Decisiones (continuar numeración en ROADMAP §7 al cerrar la ola)

| # | Decisión | Por qué |
|---|---|---|
| D49 | **El parser 4.0 captura el complemento `EstadoDeCuentaCombustible` como campo INTERNO** `data["EstadoCuentaCombustible"]`: un dict con el encabezado y una lista `Conceptos` de dicts, claves = nombres oficiales del XSD y `Traslados` como lista. Mismo contrato que `ConceptosDetalle` (D25): no va al Excel ni al visor y se excluye igual que `CFDI_Type`. **Aditivo**: ninguna columna existente cambia de valor, incluida `Combustible` | Sin esto no hay reporte. Respetar D25 deja que F4 lo guarde mañana sin volver a abrir XML (en F4 entra a `extras`/`conceptos.complemento`; si la cardinalidad lo pide, tabla propia como `pagos_doctos`, §14.4.5) |
| D50 | **Modelo único "línea de desglose"**: TODO CFDI se aplana a líneas. Una factura normal da una línea por `Concepto`. Un CFDI con ECC da su(s) concepto(s) propios (la comisión, `origen=CFDI`) **más** una línea por carga (`origen=ECC`). El reporte nunca necesita saber si es Edenred, Walmart o Home Depot | Un solo motor sirve para el caso de uso genérico y para el monedero. Si mañana aparece otro complemento con detalle (vales de despensa, etc.), solo se agrega un "aplanador", sin tocar agregaciones ni exporter |
| D51 | **Mes ancla del reporte = mes del CFDI** (`Fecha` del comprobante, igual que las carpetas de la bóveda y el PT). La `Fecha` de cada carga sale como columna informativa | Coherencia con la bóveda (cargas el mes X y ves el mes X) y con el PT. En las muestras, todas las cargas caen en el mes del CFDI. **Confirmado por el dueño 2026-10-27 (P1)** |
| D52 | **Reporte = archivo Excel APARTE** (`Desglose_<RFC>_<periodo>.xlsx` en `REPORTS_DIR`), con su propio botón. **El Excel principal no se toca** | D11: el Excel principal y sus hojas PT (D34) alimentan fórmulas INDEX/MATCH del dueño. Meter hojas de miles de filas ahí lo rompe o lo vuelve lento |
| D53 | **Alcance = el lote cargado** (lo marcado en el árbol de la bóveda). "Por mes" o "por ejercicio" = marcar esos meses o usar el preset "Año completo". Jerarquía D21 intacta: un RFC y una dirección (default Recibidas). Sin SQLite (F4 pendiente) no se recorren carpetas por fuera del lote | Cero motor nuevo de búsqueda. Cuando llegue F4/F5 la misma capa pura recibe filas de la DB en lugar de `ProcessResult` |
| D54 | **El IVA es protagonista del reporte** (P3, el dueño hará material de análisis con él). Hoja **IVA** propia en el Desglose (§3.3) que separa **siempre** el IVA del CFDI (p. ej. la comisión: $148.80) del IVA del complemento (la gasolina: $3,791.92). Nunca se suman en silencio: total = las dos columnas visibles | Si se mezclan, el lector no puede explicar de dónde salen $3,940.72 de IVA en una factura cuyo "Total" dice $1,078.80. Mismo principio que la columna NC visible de D33 |
| D55 | **El ECC entra al PT-Recibidas (etapa 4), con compuerta fiscal.** Las cargas del complemento cuentan como gasto de combustible y su IVA como acreditable en el mes del CFDI (D51/D31: estado de cuenta PUE). Van en columnas **propias y visibles** del resumen mensual ("Combustible monedero" e "IVA combustible monedero"), no revueltas con las facturas normales. **Compuerta:** la etapa 4 NO se construye hasta que los fundamentos de §8.1 estén verificados TEXTUALMENTE en `fundamentos-legales` (regla §13.1 / D32). La etapa 1–3 no depende de esto | El dueño lo pidió explícitamente ("es parte del chiste"). La compuerta existe porque el PT emite semáforos de deducibilidad: una regla fiscal citada de memoria ahí es peor que no tenerla |

---

## 3. Capas (respeta §5.3: la UI no conoce el formato)

```
parsers/xml_parser_40.py      + _extract_estado_cuenta_combustible()  (D49)
        │  data["EstadoCuentaCombustible"]  (interno)
        ▼
reports/desglose_conceptos.py  PURO, sin Qt ni openpyxl
        │  aplanar_lote() → [LineaDesglose]   +   agregaciones
        ▼
exporters/desglose_exporter.py  Excel (openpyxl), hojas de §5
        ▲
ui/reportes_page.py  botón "Desglose de conceptos…"  → diálogo
ui/results_view.py   menú contextual "Ver desglose de este XML"
```

### 3.1 Parser (ola corta; tag `v0.2.x-pre-ecc` ANTES)

- Registrar el namespace `ecc12` = `http://www.sat.gob.mx/EstadoDeCuentaCombustible12`.
- Nueva función privada hermana de `_extract_conceptos_detalle`. Si no hay
  complemento, el campo vale `None` (no lista vacía), para distinguir "no
  aplica" de "venía vacío".
- **Versión 1.1 (`ecc11`) y parser 3.3: FUERA de alcance.** El dueño no
  tiene estados de cuenta anteriores (P4). Si algún día aparece uno, se
  audita contra su XSD como en §13.1, sin adivinar su estructura. El aplanado
  genérico de conceptos (D50) **NO** cubre hoy CFDI 3.3: verificado, el
  parser 3.3 no produce `ConceptosDetalle` (solo lo hace el 4.0, F2.6). Un
  CFDI 3.3 en el lote sale en la hoja Cuadre como "3.3 — sin detalle por
  concepto" y no se inventan líneas. Agregar `ConceptosDetalle` al 3.3 es
  una mini-ola aparte (con tag D20), y el XML 3.3 multi-concepto que el dueño
  traerá de su otra computadora sería su fixture (anonimizado como §5).
- Agregar `docs/ecc12.xsd` (fuente oficial del SAT) a la carpeta de
  referencia, como se hizo con los demás XSD (D23). Así se sabe qué significa
  cada código de `TipoCombustible` **leyendo el XSD, no de memoria**.

### 3.2 Capa pura `reports/desglose_conceptos.py`

**`LineaDesglose`** (dict plano, una fila de la hoja Detalle):

| Grupo | Campos |
|---|---|
| Comprobante | `uuid`, `serie`, `folio`, `fecha_cfdi`, `anio`, `mes`, `rfc_emisor`, `nombre_emisor`, `tipo_comprobante`, `forma_pago`, `metodo_pago` |
| Línea | `origen` (`CFDI`/`ECC`), `num_linea`, `clave_prod_serv`, `descripcion` (en ECC: `NombreCombustible`), `cantidad`, `clave_unidad`/`unidad` (en ECC: "L"), `valor_unitario`, `importe`, `descuento`, `iva_trasladado` (suma de traslados 002/"IVA"), `ieps`, `retenciones`, `total_linea` |
| Solo ECC | `tarjeta` (`Identificador`), `rfc_estacion`, `clave_estacion`, `tipo_combustible`, `folio_operacion`, `fecha_carga` |
| Clasificación | `categoria`: "Combustible (monedero)" para ECC; "Combustible" si R8 da verdadero; en los demás casos, la `descripcion` tal cual. **No se inventan nombres de familias de `ClaveProdServ`**: `catCFDI.xsd` no trae descripciones (D23) |

Reglas de aplanado:
- Moneda: todo en MXN vía `Tipo De Cambio`, igual que el PT (D31).
- Tipo E (nota de crédito): sus líneas salen con **importes en negativo** y
  `tipo_comprobante="E"`, para que las sumas por proveedor sean netas. Tipo P
  y N **no entran** (no tienen conceptos de gasto).
- Descuento 100% (etiqueta TAG): la línea entra con total 0, no se filtra.
- **Impuestos locales (hallazgo de la etapa 2):** un CFDI con complemento
  `implocal` (ej. ISH de un hotel: $2,689.60 + IVA $430.34 + ISH $80.69 =
  $3,200.63) tiene un Total que NO es la suma de sus conceptos. El impuesto
  local no cuelga de ningún concepto, así que entra como una **línea
  explícita** "IMPUESTOS LOCALES (neto, no por concepto)", categoría
  "Impuestos locales", con `total_linea` = trasladado local − retenido local.
  Sin ella, el cuadre fallaba (verificado con `XML-Test/9A655B6C…`).

**Agregaciones** (funciones puras que reciben la lista de líneas):

| Función | Agrupa por | Métricas |
|---|---|---|
| `por_xml(uuid)` | líneas de un comprobante | todas, más fila de cuadre |
| `por_proveedor` | `rfc_emisor` | nº CFDI, nº líneas, importe, IVA, total |
| `por_mes` | `anio-mes` × `rfc_emisor` | ídem |
| `por_ejercicio` | `anio` × `rfc_emisor` | ídem |
| `por_concepto` | `rfc_emisor` × `clave_prod_serv` × `descripcion` | cantidad, importe, IVA (sirve para "qué le compro a Home Depot") |
| `combustible` | mes × `tipo_combustible`, mes × `tarjeta`, `rfc_estacion` | litros, importe, IVA, **precio promedio por litro** = importe / litros |
| `cuadre` | uuid | Σ importes de las líneas vs `SubTotal` (CFDI) y Σ ECC vs `SubTotal`/`Total` del complemento. Tolerancia ±$0.05 por redondeo. Fuera de tolerancia = "No cuadra" |

### 3.3 Exporter `exporters/desglose_exporter.py`

Archivo nuevo, con autofiltro y encabezado congelado en cada hoja. Catálogos
SAT con el formato "código - descripción" (D47):

1. **Detalle**: todas las `LineaDesglose`, una por fila. Es la base para que
   el contador haga su tabla dinámica.
2. **Por proveedor**, 3. **Por mes**, 4. **Por ejercicio**, 5. **Por concepto**.
6. **Combustible**: solo si hay líneas ECC. Tres bloques: por tipo, por
   tarjeta y por estación.
7. **IVA** (D54), siempre presente. Por mes × proveedor, con columnas
   **IVA del CFDI**, **IVA del complemento (combustible monedero)** e **IVA
   total**, más base gravable y desglose por tasa (16% / 8% / 0% / exento,
   mismo criterio que D48). Una fila de totales del periodo. Es la hoja
   pensada para material de análisis: se lee sola, sin abrir las demás.
8. **Cuadre**: solo los UUID que no cuadran, o la leyenda "Todos cuadran".

Totales con fórmula `=SUBTOTAL(9, …)`: suman solo lo visible al filtrar.
Nombre: `Desglose_<RFC>_<AAAA-MM>[_a_<AAAA-MM>].xlsx` derivado del lote,
mismo criterio que D29/F2.7.

### 3.4 UI

- **Página Reportes**: botón primario nuevo **"Desglose de conceptos…"**.
  Deshabilitado con tooltip "Carga meses en la bóveda primero" si no hay
  lote. Abre un diálogo con:
  - Proveedor: combo "Todos" + los RFC emisores del lote con su conteo
    (p. ej. `ASE930924SS7 – EDENRED MEXICO (5)`).
  - Hojas: casillas para cada hoja de §3.3, todas marcadas por default.
  - Botón **Guardar Excel…**.
- **Visor, pestaña Facturas**: menú contextual (clic derecho) **"Ver desglose
  de este XML"**. Abre un diálogo modal con la tabla de líneas de ese UUID
  (las 33 cargas en el caso Edenred), totales y semáforo de cuadre, más el
  botón "Exportar este XML". Esto cubre el "reporte por XML" sin exportar
  todo.
- La página **no** conoce `ProcessResult`. `main_window` le pasa la lista de
  `parsed_data` (patrón de señales existente, como `open_reports_folder`).

---

## 4. Lo que F2.10 NO hace (el constructor no inventa alcance)

- **No cambia la columna `Combustible` del visor/Excel** (D11). El PT sí
  cambia, pero solo en la etapa 4 y detrás de la compuerta de D55.
- No detecta duplicados con facturas que la gasolinera haya emitido directo
  al contribuyente en las etapas 1–3. La advertencia llega en la etapa 4
  (§8.3).
- No desglosa telepeaje por caseta: el XML no lo trae. Solo cruces × importe.
- No consulta SQLite ni recorre carpetas fuera del lote (D53).

---

## 5. Pruebas mínimas

**Fixtures YA anonimizados y comiteados** (P2) en `tests/fixtures/edenred/`,
uno por UUID. **No van en `XML-Test/`**: `core.process_path` recorre esa
carpeta de forma recursiva y cambiaría los conteos de `test_core` y
compañía. Anonimización aplicada:

| Dato | Reemplazo |
|---|---|
| RFC receptor | `GAGG010101000` (convención de `XML-Test/`) |
| Nombre receptor | `RECEPTOR GASOLINA PRUEBA` |
| DomicilioFiscalReceptor | `01000` |
| `NumeroDeCuenta` (ECC) | `00000000000001` |
| `Identificador` (tarjetas) | `9999000000000001`…`05`, **consistente entre archivos** (la misma tarjeta da el mismo número falso), así la agrupación por tarjeta sigue siendo probable |
| `Sello`, `SelloCFD`, `SelloSAT`, `Certificado` | `ANONIMIZADO` (el parser los guarda pero no los valida) |

Importes, fechas, UUID, RFC de gasolineras, litros y precios quedan
**intactos**: son lo que se prueba. Falta un fixture multi-concepto tipo
Walmart/Home Depot: o uno de `XML-Test/` con varios conceptos, o el 3.3
que traerá el dueño.

1. `3358E192`: 33 líneas ECC + 1 comisión; Σ importe ECC = 24,393.77;
   Σ IVA = 3,791.92; litros = 1,127.97; cuadre OK.
2. `46613d69`: agrupa "Magna" y "BP REGU" bajo el mismo `TipoCombustible=1`.
3. Telepeaje `29D10416`: 1 línea, cantidad 37, sin bloque ECC.
4. Etiqueta TAG `57A56A0B`: total 0, no truena, no se filtra.
5. XML sin complemento: `EstadoCuentaCombustible is None` y **todas las
   columnas existentes salen byte-idénticas** que antes (regresión D11).
6. Nota de crédito tipo E: resta en "Por proveedor".
7. Cuadre forzado a fallar (fixture alterado) → aparece en la hoja Cuadre.

---

## 6. Orden de construcción (4 commits, cada uno verde)

1. **Parser** (tag primero) + pruebas 1, 2 y 5.
2. **Capa pura + exporter (incluida la hoja IVA)** + pruebas 3, 4, 6 y 7, y
   botón en Reportes.
3. **Diálogo "Ver desglose de este XML"** en el visor.
4. **ECC en PT-Recibidas** (D55): solo después de pasar la compuerta de §8.1.

---

## 6.1 Estado de construcción

| Etapa | Estado |
|---|---|
| 1 Parser ECC | ✅ 2026-10-27 (tag `pre-f2.10-ecc`) |
| 2 Capa pura + Excel + botón en Reportes | ✅ 2026-10-27 (`reports/desglose_conceptos.py`, `exporters/desglose_exporter.py`, `ui/desglose_dialog.py`). Pruebas verdes; **la parte Qt (botón y diálogo) NO se pudo ejecutar en el contenedor** (sin `libEGL`) y falta probarla en la máquina del dueño |
| 3 Diálogo "Ver desglose de este XML" | ✅ 2026-10-28 (clic derecho en Facturas → `ui/desglose_xml_dialog.py`; helpers puros `tabla_xml`/`resumen_xml`/`texto_pie_xml`). Pruebas puras verdes; las de UI (`tests/test_f210_desglose_xml_ui.py`) se omiten en el contenedor y **faltan correrlas en la máquina del dueño** |
| 4 ECC en PT-Recibidas | ✅ 2026-10-28 (`reports/pt_recibidas.py`, `exporters/pt_exporter.py`, tag `pre-f2.10-etapa4`). F1 y F3 verificados con el texto oficial de la regla 3.3.1.7; **F2 y F4 siguen pendientes**, así que el IVA del monedero se muestra pero no se suma |

## 6.2 Cómo se consulta (aclaración pedida por el dueño, 2026-10-27)

Ya estaba decidido en D53; aquí se pone completo para que no quede implícito:

1. **No hay búsqueda nueva.** El reporte opera sobre el lote que ya está
   cargado en la app, y ese lote se arma como siempre: Administrador de
   Bóveda → árbol RFC / Emitidas·Recibidas / año / mes (casillas en meses,
   presets de bimestre/trimestre/semestre/año completo) → Cargar.
2. **Por mes** = marcar ese mes. **Por ejercicio** = preset "Año completo".
   Las hojas "Por mes" y "Por ejercicio" ya traen la separación; no hace falta
   cargar mes por mes.
3. **Por proveedor** = combo del diálogo (los emisores que hay en el lote, con
   su número de CFDI). Un RFC y una dirección a la vez (D21, jerarquía dura).
4. **Por XML** = etapa 3 (clic derecho en el visor).
5. **Lo que NO existe todavía:** buscar texto libre en los conceptos ("tornillo")
   o consultar sin cargar el lote. Eso es F5 (SQLite + FTS5, D21/D24) y se
   diseña ahí; esta fase deja la capa pura lista para recibir filas de la base
   en lugar de `ProcessResult`. **No se requiere Opus para esto**: ya está
   dentro del diseño existente.

## 6.3 Visor del desglose del LOTE (pedido del dueño, 2026-10-28)

Tras probar el clic derecho ("solo de ese XML"), el dueño pidió ver **todo el
lote, filtrado, con el RFC y la factura que contiene cada concepto**. Esto
**adelanta** parte de lo que §6.2 dejaba para F5: la búsqueda de texto libre
sobre los conceptos, pero solo sobre el lote ya cargado (sin SQLite).

- **Dónde:** botón **"Desglose del lote…"** en la pantalla del Administrador de
  Bóveda, junto a "Guardar filtrado…" (se habilita igual que "Guardar
  Excel…"). Antes la única entrada era Inicio → Reportes y no se encontraba.
- **Qué muestra:** ventana con caja de búsqueda y un **árbol**: Proveedor (RFC)
  → Factura (folio + UUID) → líneas (concepto, o carga con fecha, tarjeta y
  estación). Cada nodo suma importe, IVA y total de lo que se ve.
- **Búsqueda:** mismo comportamiento que el resto de la app (`ui/filtering.py`):
  texto libre sobre RFC, proveedor, factura, UUID, concepto, clave, categoría,
  tarjeta y estación; y montos `total>=5000`, `iva<100`, `cantidad>10`.
- **Interacción:** doble clic o menú contextual en una factura/línea → abre el
  desglose de ESE XML (el diálogo de la etapa 3). Con búsqueda activa se
  expande todo (hasta 1,500 líneas; arriba de eso se avisa y se expande a
  mano). Las líneas de cada factura se crean al expandirla.
- **"Exportar lo filtrado…":** Excel con lo que se ve (Detalle, resúmenes,
  Combustible, IVA). **Sin la hoja Cuadre**, porque compara contra el Total
  del CFDI completo y con solo algunas líneas saldría "no cuadra" por error.
  Nombre: `Desglose_<RFC>_<periodo>_filtrado-<texto>.xlsx`.
- **Capas:** `filtrar_lineas`, `arbol`, `texto_resumen_lote` (puras, en
  `reports/desglose_conceptos.py`), `exportar_desglose_lineas` (exporter) y
  `ui/desglose_lote_dialog.py` (solo pinta).

## 7. Respuestas del dueño (2026-10-27)

- **P1** Mes ancla = **mes del CFDI** → D51 confirmada.
- **P2** **Anonimizar** → hecho, ver §5.
- **P3** **Sí**: el ECC entra al análisis fiscal y el IVA es central (el
  dueño hará material con esto) → D54 y D55.
- **P4** **No hay** XML antiguos de Edenred → `ecc11` y 3.3 fuera de alcance
  (§3.1). El dueño puede traer de otra computadora un XML antiguo
  multi-concepto (no gasolina): sirve como fixture del aplanado genérico.

---

## 8. Etapa 4 — ECC en el PT-Recibidas (diseño detallado 2026-10-28)

### 8.0 Decisiones nuevas

| # | Decisión | Por qué |
|---|---|---|
| D56 | **La compuerta fiscal se vuelve un DATO, no un bloqueo de construcción.** La etapa 4 se construye YA. Los cuatro fundamentos F1–F4 viven en una tabla `FUNDAMENTOS_ECC` de `pt_recibidas.py` con la cita en `None`. Mientras **alguna** cita sea `None`: las cifras del monedero **se muestran** en columnas propias con semáforo ámbar "pendiente de verificar fundamento", y **no se suman** al IVA acreditable. Cuando las cuatro tengan cita textual verificada, el semáforo pasa a verde y la fórmula del total las incluye. Llenar las citas es un cambio de 4 renglones, sin tocar lógica. Sustituye a la regla de D55 de "no construir hasta verificar" | El dueño quiere ver las cifras ya, para su material. La regla anti-alucinación (§13.1 / D32) sigue intacta: ninguna cita se escribe de memoria, y ningún número no verificado entra a un total fiscal. Esperar a la verificación para escribir código no protegía nada que esto no proteja |
| D57 | **Forma de pago efectiva de las cargas = `05 - Monedero electrónico`**, bancarizada por catálogo (verificado en `docs/catalogos_filtrados.md`: código 5, columna Bancarizado = "Sí"). La `FormaPago=03` del CFDI es la de la **comisión**, no la de la gasolina, y no se usa para las cargas. Que el 05 cumpla LISR 27-III párr. 2 es justo F2: hasta verificarlo, ámbar | El catálogo sí está en el repo y se pudo verificar. El texto de la ley no. Se separan las dos cosas |
| D58 | **Ninguna columna existente del PT cambia de valor, haya o no ECC en el lote.** `subtotal_neto`, `total_neto`, `iva_neto`, `iva_acreditable_estimado`, los buckets PUE/PPD y el estatus de la comisión salen idénticos. El monedero vive SOLO en columnas nuevas, más una fórmula de total que suma ambas a la vista | D11 y D54. Si `iva_acreditable_estimado` absorbiera el ECC, nadie podría reconstruir de dónde salió la cifra ni comparar contra un PT viejo |

### 8.1 Compuerta fiscal: qué hay que verificar y dónde

Fuente: `fundamentos-legales` en la máquina del dueño (la carpeta de D32;
el PT ya cita de ahí `RMF_2026-DOF-28122025.md`). **Desde la nube no hay
acceso a esa carpeta**, y los portales fiscales están fuera de la red de la
sesión. La verificación la hace una sesión local (Claude Desktop o
`claude remote-control` en la PC del dueño) o el dueño sube el `.md` al repo.

| # | Qué hay que encontrar escrito | Pista para buscar (NO verificada) |
|---|---|---|
| F1 | La regla de la RMF vigente que permite **comprobar el combustible pagado con monedero electrónico** con el CFDI del emisor del monedero más el complemento `EstadoDeCuentaCombustible` | Buscar "monedero electrónico" en la RMF 2026. Fuentes secundarias apuntan a la sección 3.3.1: 3.3.1.6 (concepto) y la regla siguiente (comprobación). **La numeración cambia por año: confirmar contra el texto vigente** |
| F2 | Que pagar con monedero **cumple la bancarización del combustible** (LISR 27-III párr. 2) | Mismo artículo ya citado en R2, más la regla de F1. Fuentes secundarias dicen que la LISR acepta monederos autorizados por el SAT como medio de pago del combustible |
| F3 | Que el **IVA de cada carga es acreditable** con ese CFDI, y en **qué mes** | LIVA 5 (ya citado en R3) más la regla de F1. Fuentes secundarias dicen que el IVA "sigue la suerte de la deducción". El mes debe salir del texto: si no lo dice, se queda el mes del CFDI (D51) con nota |
| F4 | Si el **permiso de la Ley de Hidrocarburos** (D32) aplica y cómo se cumple con monedero | El complemento trae `Rfc` y `ClaveEstacion`, **no** el número de permiso. Si la regla de F1 lo exime o lo da por cumplido con `ClaveEstacion`, citarlo. Si no, es un faltante real y el semáforo se queda ámbar con esa leyenda |

Las pistas salen de una búsqueda web y no son fuente: sirven para saber qué
buscar, nunca para citar.

### 8.2 Contrato de construcción (`reports/pt_recibidas.py`, todo aditivo)

**Constantes nuevas:**
- `FORMA_MONEDERO = "05"` (D57).
- `FUNDAMENTOS_ECC`: lista ordenada de `(id, criterio, cita)` para F1–F4,
  con `cita=None` hasta verificar.
- `ecc_fundamentado()`: `True` solo si las cuatro citas no son `None`.
- Estatus nuevos, con su nivel en `ESTATUS_NIVEL`:
  - `ESTATUS_ECC_DEDUCIBLE = "Combustible monedero: deducible"` (verde).
  - `ESTATUS_ECC_PENDIENTE = "Combustible monedero: pendiente de verificar fundamento"` (ámbar).
  - `ESTATUS_ECC_PROVISIONADO` y `ESTATUS_ECC_GENERICO` reusan la lógica de
    la comisión: si la comisión es XAXX, las cargas son rojo "no deducible:
    receptor genérico"; si es PPD sin REP, ámbar "provisionado".

**`clasificar_recibida`** sigue igual para la comisión. Además agrega, con
cero/`None` cuando no hay ECC:
- `ecc_cargas` (int), `ecc_litros`, `ecc_importe_mxn`, `ecc_iva_mxn`,
  `ecc_total_mxn`: sumas de `EstadoCuentaCombustible.Conceptos` × tipo de
  cambio (mismo `_a_mxn`).
- `ecc_estatus` / `ecc_nivel`: el estatus de la comisión manda si es
  XAXX/provisionado. Si no, verde o ámbar según `ecc_fundamentado()`.
- `ecc_iva_acreditable_mxn` = `ecc_iva_mxn` **solo** si `ecc_estatus` es
  verde; en otro caso 0.

**`construir_resumen_mensual`**: tres claves nuevas en
`_fila_resumen_vacia`, todas en el **mes de emisión** (D51, PUE). Un ECC PPD
seguiría a su REP como el resto (no hay caso real hoy, pero la regla ya
existe en D31):
- `combustible_monedero` = Σ `ecc_total_mxn` (con IVA, igual que los demás
  buckets del resumen).
- `iva_combustible_monedero` = Σ `ecc_iva_mxn` (siempre visible).
- `iva_monedero_acreditable` = Σ `ecc_iva_acreditable_mxn` (0 mientras la
  compuerta esté abierta).

**Posible duplicado (§8.3), función pura `marcar_posibles_duplicados(detalle)`:**
para cada fila del detalle cuyo `rfc_emisor` sea un `Rfc` de estación de
alguna carga del lote, si `|total_mxn − (importe+IVA de la carga)| ≤ 0.05` y
la fecha de emisión cae entre 0 y 31 días después de la `Fecha` de la carga,
pone `posible_duplicado_monedero` = folio de la factura del monedero
(`Factura` del CFDI con ECC). Es una advertencia: no cambia estatus ni resta.

### 8.3 Contrato del exporter (`exporters/pt_exporter.py`)

- **Resumen** (`_COLS_RESUMEN`), al final y en este orden:
  "Combustible monedero", "IVA combustible monedero", "IVA monedero
  acreditable" y **"IVA acreditable estimado + monedero"**. Esta última es
  **fórmula viva** `=<col iva_acreditable_estimado> + <col iva_monedero_acreditable>`
  (D34), nunca un valor ya sumado.
- Encabezados ámbar con la nota "(pendiente de verificar fundamento)"
  mientras `ecc_fundamentado()` sea `False`.
- **Detalle** (`_COLS_DETALLE`), al final: "Cargas ECC", "Litros ECC",
  "Importe ECC", "IVA ECC", "Estatus ECC" (con el color de `ecc_nivel`) y
  "Posible duplicado monedero".
- **Fundamentos**: cuatro renglones F1–F4. La cita verificada si existe; si
  no, el texto literal "PENDIENTE DE VERIFICAR — no se cita de memoria (F2.10
  §8.1)". Más una nota: "La deducción de automóviles con tope (LISR 36) y el
  IEPS del combustible NO se calculan en este PT".
- Columnas ECC visibles aunque el lote no tenga ECC (todas en 0). Así el
  layout del PT es estable y las fórmulas INDEX/MATCH del dueño no cambian de
  columna según el mes.

### 8.4 Pruebas obligatorias

1. **Regresión D58:** con los fixtures de `XML-Test/` y con los de Edenred,
   todas las claves que ya existían en resumen y detalle valen **exactamente
   lo mismo** que en el tag/commit anterior a la etapa 4. Mismo método de
   comparación que en la etapa 1: correr las dos versiones y comparar.
2. Junio: `combustible_monedero` = 28,185.69 e `iva_combustible_monedero` =
   3,791.92. Agosto: 40,447.09 y 5,441.49.
3. Con la compuerta abierta (citas `None`): `iva_monedero_acreditable` = 0,
   `ecc_estatus` ámbar, y la fórmula del Excel suma 0.
4. Con las cuatro citas parcheadas en la prueba (monkeypatch de
   `FUNDAMENTOS_ECC`): `iva_monedero_acreditable` = `iva_combustible_monedero`
   y el estatus es verde. **El código de producción NO se parchea.**
5. Comisión XAXX → cargas rojo genérico. Comisión PPD sin REP → cargas ámbar
   provisionado.
6. Duplicado: un CFDI sintético de la estación `OMC100818GZ7` por $1,445.88,
   emitido el 2026-06-25 → marcado con `TCGE-000004231229`. El mismo con
   $1,445.00 o emitido 40 días después → no marcado.
7. Excel: existen las columnas nuevas, la celda de total es fórmula
   (empieza con `=`), y la hoja Fundamentos dice "PENDIENTE DE VERIFICAR" ×4.

### 8.5 Fuera de alcance (no inventar)

- Tope de deducción de automóviles y proporción del IVA (LISR 36): requiere
  datos del vehículo que el CFDI no trae.
- IEPS del combustible: el complemento de las muestras no lo desglosa.
- Conciliación contra el estado de cuenta bancario (D22).

### 8.6 Orden de construcción

1. Tag `pre-f2.10-etapa4` (D20: toca el PT).
2. `pt_recibidas.py` + pruebas 1 a 6.
3. `pt_exporter.py` + prueba 7.
4. Verificación F1–F4 en sesión local. Si pasa, llenar las 4 citas en
   `FUNDAMENTOS_ECC`. Ese es el único cambio para pasar a verde.

### 8.7 Resultado de la verificación (2026-10-28)

El dueño pegó el texto oficial de las reglas **3.3.1.6** (concepto de monedero
electrónico) y **3.3.1.7** (deducción de combustibles con monedero) de la RMF
2026, copiado de la página del SAT. Se registró como cita en
`FUNDAMENTOS_ECC` marcado como "texto proporcionado por el dueño; cotejar con
el DOF para dictamen".

| # | Resultado | Qué dice el texto |
|---|---|---|
| F1 | ✅ Verificado | 3.3.1.7 párr. 1: la comisión se comprueba con el CFDI y el pago de los combustibles con el complemento de estado de cuenta; las estaciones no emiten CFDI al cliente por esas operaciones |
| F2 | ⏳ Pendiente | Las reglas se emiten "para los efectos del 27-III primer y segundo párrafos", pero **no dicen** textualmente que pagar con monedero sea pago bancarizado. Falta el texto de la LISR 27-III párr. 2 |
| F3 | ✅ Verificado (con matiz) | 3.3.1.7 párr. 2: la deducción y el acreditamiento proceden "hasta que… cuente con el CFDI y el complemento… y hasta por el monto que ampare el citado complemento" |
| F4 | ⏳ Pendiente | El texto no menciona el permiso de la Ley de Hidrocarburos |

**Consecuencia:** `ecc_fundamentado()` sigue en `False` (exige F1–F4). El IVA
del monedero se muestra ($3,791.92 en junio, $5,441.49 en agosto) y la columna
"IVA monedero acreditable" vale 0. Para pasar a verde solo hay que reemplazar
los dos `None` de `FUNDAMENTOS_ECC` (F2 y F4) por su cita textual, y actualizar
la prueba `test_f1_y_f3_citan_la_regla_3_3_1_7_y_f2_f4_siguen_pendientes`.

**Matiz de F3 (hallazgo, decisión del dueño pendiente):** los dos estados de
cuenta de las muestras se emiten el último día del mes y se **timbran al día
siguiente** (junio: emitido 30/06, timbrado 01/07; agosto: 31/08 → 01/09). La
regla permite acreditar "hasta que" se cuente con el CFDI y el complemento. El
PT sigue anclando al mes de emisión (P1, decisión del dueño), pero muestra la
columna "Mes de timbrado (ECC)" resaltada cuando difiere. Qué mes usar para el
acreditamiento es criterio fiscal; no se asume.

**Efecto en §8.3:** la regla confirma que la estación **no** debe emitir CFDI
por operaciones con monedero, lo que respalda la advertencia de posible
duplicado.
