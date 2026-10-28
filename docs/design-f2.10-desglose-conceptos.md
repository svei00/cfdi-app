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
| 4 ECC en PT-Recibidas | Pendiente (compuerta §8.1) |

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

## 7. Respuestas del dueño (2026-10-27)

- **P1** Mes ancla = **mes del CFDI** → D51 confirmada.
- **P2** **Anonimizar** → hecho, ver §5.
- **P3** **Sí**: el ECC entra al análisis fiscal y el IVA es central (el
  dueño hará material con esto) → D54 y D55.
- **P4** **No hay** XML antiguos de Edenred → `ecc11` y 3.3 fuera de alcance
  (§3.1). El dueño puede traer de otra computadora un XML antiguo
  multi-concepto (no gasolina): sirve como fixture del aplanado genérico.

---

## 8. Etapa 4 — ECC en el PT-Recibidas

### 8.1 Compuerta fiscal: verificar TEXTUALMENTE antes de construir

En `fundamentos-legales` (la carpeta de D32) se busca el texto vigente de
cada punto y se cita literal en la hoja Fundamentos. Si un punto no se
encuentra, **no se codifica como regla**: se muestra como "pendiente de
verificar" en el semáforo.

| # | Qué hay que encontrar escrito | Por qué importa |
|---|---|---|
| F1 | La regla de la RMF vigente que permite **comprobar el combustible pagado con monedero electrónico** mediante el estado de cuenta del emisor autorizado con el complemento `EstadoDeCuentaCombustible` | Sin ella, las cargas no son deducibles con ese CFDI. Es la base de toda la etapa |
| F2 | Si ese pago con monedero **cumple el requisito de bancarización del combustible** (LISR 27-III párr. 2, ya citado en D32) | R2 del PT marca combustible no bancarizado como no deducible. El CFDI dice `FormaPago=03` pero paga la comisión, no la gasolina |
| F3 | Si el **IVA de cada carga del complemento es acreditable** con ese CFDI y en qué mes | Es el número central del material del dueño. El mes propuesto (CFDI, D51) debe salir del texto, no de la intuición |
| F4 | Si el requisito del **permiso de la Ley de Hidrocarburos** (D32) aplica aquí y cómo se cumple | El complemento trae `Rfc` y `ClaveEstacion` de la gasolinera, pero **no** el número de permiso. Podría ser un faltante real |

### 8.2 Cambios al PT una vez pasada la compuerta (aditivos, D11)

- `reports/pt_recibidas.py`: el CFDI con ECC sigue clasificándose por su
  comisión como hoy. **Además** aporta las cargas como un monto aparte
  ("combustible monedero") con su IVA. La clasificación de la comisión no
  cambia.
- Resumen mensual: dos columnas nuevas visibles, "Combustible monedero" e
  "IVA combustible monedero", al lado de las actuales. **El IVA acreditable
  total = columna actual + columna nueva**, con fórmula visible (D34: el PT
  lleva fórmulas reales), nunca un número ya sumado.
- Detalle: una fila por CFDI como hoy, con dos columnas nuevas (litros e
  importe ECC). El renglón por carga vive en el Desglose, no en el PT.
- Semáforo propio para el ECC según F1–F4: verde si todo está verificado,
  amarillo "pendiente de verificar" si falta algún fundamento.
- Pruebas: los dos estados de cuenta de los fixtures suman al resumen de su
  mes exactamente lo de §1 ($24,393.77 + $3,791.92 en junio y $35,005.60 +
  $5,441.49 en agosto). Además, el resumen de un lote sin ECC sale
  **idéntico** al de antes (regresión).

### 8.3 Riesgo de doble conteo (advertencia, no regla)

Si la gasolinera **también** le facturó directo al contribuyente una carga
pagada con monedero, el gasto aparecería dos veces. La etapa 4 agrega una
advertencia en el detalle: Recibida cuyo emisor es un `rfc_estacion` del ECC
con fecha e importe iguales a una carga → "posible duplicado con monedero".
No resta nada automáticamente: el contador decide.
