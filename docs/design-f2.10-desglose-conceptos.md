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
   real que no se resuelve en esta fase (ver §7, pregunta P3).

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
| D51 | **Mes ancla del reporte = mes del CFDI** (`Fecha` del comprobante, igual que las carpetas de la bóveda y el PT). La `Fecha` de cada carga sale como columna informativa | Coherencia con la bóveda (cargas el mes X y ves el mes X) y con el PT. En las muestras, todas las cargas caen en el mes del CFDI. Pendiente de confirmar por el dueño (P1) |
| D52 | **Reporte = archivo Excel APARTE** (`Desglose_<RFC>_<periodo>.xlsx` en `REPORTS_DIR`), con su propio botón. **El Excel principal no se toca** | D11: el Excel principal y sus hojas PT (D34) alimentan fórmulas INDEX/MATCH del dueño. Meter hojas de miles de filas ahí lo rompe o lo vuelve lento |
| D53 | **Alcance = el lote cargado** (lo marcado en el árbol de la bóveda). "Por mes" o "por ejercicio" = marcar esos meses o usar el preset "Año completo". Jerarquía D21 intacta: un RFC y una dirección (default Recibidas). Sin SQLite (F4 pendiente) no se recorren carpetas por fuera del lote | Cero motor nuevo de búsqueda. Cuando llegue F4/F5 la misma capa pura recibe filas de la DB en lugar de `ProcessResult` |

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
- **Versión 1.1 (`ecc11`, namespace sin "12")**: los Edenred anteriores
  podrían traerla. Se cubre solo si el dueño tiene esos XML (P4); no se
  adivina su estructura, se audita contra el XSD como en §13.1.
- Parser 3.3: igual, solo si P4 confirma XML de Edenred 3.3.
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
7. **Cuadre**: solo los UUID que no cuadran, o la leyenda "Todos cuadran".

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

- **No cambia el PT-Recibidas ni la columna `Combustible`** (ver P3).
- No detecta duplicados con facturas que la gasolinera haya emitido directo
  al contribuyente. Queda como mejora: cruzar `rfc_estacion` + fecha +
  importe contra las Recibidas del lote y marcar "posible duplicado".
- No desglosa telepeaje por caseta: el XML no lo trae. Solo cruces × importe.
- No consulta SQLite ni recorre carpetas fuera del lote (D53).

---

## 5. Pruebas mínimas (fixtures = los 5 XML de Edenred + 1 multi-concepto)

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

## 6. Orden de construcción (3 commits, cada uno verde)

1. **Parser** (tag primero) + pruebas 1, 2 y 5.
2. **Capa pura + exporter** + pruebas 3, 4, 6 y 7, y botón en Reportes.
3. **Diálogo "Ver desglose de este XML"** en el visor.

---

## 7. Preguntas abiertas para el dueño (no bloquean el paso 1)

- **P1** Mes ancla: ¿mes del CFDI (recomendado, D51) o mes de cada carga?
- **P2** Fixtures: los XML traen tu RFC y nombre reales. ¿Se suben así a
  `tests/fixtures/` o se anonimizan (RFC/nombre del receptor reemplazados,
  sin tocar los importes)?
- **P3** PT-Recibidas: ¿la gasolina del ECC debe entrar al IVA acreditable y
  a la deducción? Antes de tocar el PT hay que **verificar textualmente** en
  la RMF vigente la regla de comprobación de combustible con monedero
  electrónico. No se cita de memoria (§13.1 / D32). Fase aparte.
- **P4** ¿Tienes estados de cuenta de Edenred de años anteriores (CFDI 3.3 o
  complemento `ecc11`)? Si sí, entran en el paso 1.
