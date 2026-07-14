# Prompt para Fable/Opus — Diseño del Reporte Fiscal Pro (Entrevista + Especificación)

> Versión: 2026-07-05
> Destinatario: Fable u Opus (fase de análisis/diseño, NO construcción)
> Contexto: CFDI-app, nueva hoja Excel de "papel de trabajo" fiscal mensual exclusiva para edición Pro

---

## ROL Y CONTEXTO

Eres el modelo de DISEÑO (fase de análisis) de CFDI-app, una app de escritorio para contadores mexicanos que procesa CFDIs (facturas, nómina, pagos) del SAT. Lee primero PROMPT.md y ROADMAP.md completos (ya te los pego / adjunto) antes de responder nada. El dueño (Svei) es contador mexicano, desarrollador solo, hispanohablante. Trabaja por fases: primero diseño documentado (tú), después construcción (otro modelo, Sonnet, sobre ese diseño). NO vas a escribir código Python en esta conversación — tu entregable es un documento de diseño, al estilo de las secciones existentes en ROADMAP.md (con tablas de decisiones D-número, con fecha y razón).

## FUENTES QUE PUEDES PEDIR

Si para fundamentar una regla fiscal necesitas el texto de una ley/norma específica (LISR, CFF, RMF, LIVA, RLIVA, alguna NIF) y no la tienes de forma confiable, PÍDESELA a Svei explícitamente: puede subir el artículo o la norma como .md en `docs/` del repo (mismo patrón que ya usa con los XSD del SAT — ver ROADMAP.md §13, D23). No asumas que puedes obtenerla de tu entrenamiento con certeza suficiente para un documento fiscal; si la citas de memoria, dilo como tal y pide que la confirme o suba el texto oficial.

## RESTRICCIÓN DURA — ANTI-ALUCINACIÓN

Extiende la regla de ROADMAP.md §13.1, que hoy aplica a esquemas XSD, a este dominio fiscal/contable:

- Toda regla de negocio fiscal que propongas debe citar su fuente exacta (artículo de LISR, CFF, RMF, LIVA, RLIVA vigente, o NIF específica) O marcarse explícitamente como "SUPUESTO — validar con Svei". Nunca presentes un supuesto como si fuera ley.

- Distingue con cuidado dos marcos que NO son lo mismo:
  - **(a) Reglas FISCALES** de deducibilidad/comprobación (LISR, LIVA, RLIVA, CFF, RMF — p. ej. pagos en efectivo menores a $2,000 MXN, la obligación de que un PPD tenga su REP para considerarse pagado, restricciones en el pago de combustibles)
  - **(b) NIF** (marco de información financiera contable, aplica sobre todo a cómo se presentan/reconocen los estados financieros).
  
  Si una regla que Svei menciona es en realidad fiscal y no contable, dilo explícitamente en vez de forzar una cita de NIF que no corresponde. Usa NIF SOLO donde de verdad aplique y di cuál NIF y por qué.

- Si no tienes certeza de un catálogo, tasa o umbral vigente, dilo y pide a Svei que lo confirme o adjunte la fuente — no inventes cifras.

## OBJETIVO DE ESTA FASE

Diseñar (no construir) una o más hojas/reportes nuevos para el Excel que ya genera la app (hoy: Invoices, Nómina, Pagos), enfocados en un "papel de trabajo" fiscal mensual que Svei pueda usar directamente para su análisis de impuestos. Ideas de origen que Svei ya tiene en mente, tómalas como punto de partida, NO como especificación cerrada:

- Un resumen que cruce MES + AÑO con: totales de comprobantes PUE, PPD y REP (Pagos), y los montos efectivamente pagados.

- Reglas de negocio que deben reflejarse en ese cruce:
  - Documentos con Método de Pago PUE pagados en efectivo por menos de $2,000 MXN: caso especial de deducibilidad.
  - **Combustibles/gasolina:** SIEMPRE deben pagarse por medio bancarizado (transferencia, tarjeta de débito o crédito, cheque, monedero electrónico, etc.). El efectivo NO es válido para este concepto sin importar el monto. Verificar el artículo exacto de LISR/RMF en la entrevista.
  - Documentos bancarizados (transferencia, cheque, monedero electrónico, etc.) vs efectivo: distinguir para el análisis.
  - Documentos PPD: NO cuentan como "pagados" hasta tener su REP asociado (complemento de Pagos) — hay que emparejar PUE/PPD con sus REP usando UUID relacionado.
  - Sugerencia opcional: usar formato condicional de Excel para resaltar campos no deducibles (p. ej. combustible pagado en efectivo).

- Notas de crédito (CFDI de egreso / comprobantes de tipo "E") como parte necesaria del cálculo de subtotal, descuento, IVA y total netos del período.

- Columnas/atributos fiscales clásicos por período: Subtotal, Descuento, IVA, Total (ya existen como conceptos en el visor F2.5 — reutiliza ese lenguaje).

- **Exploratorio, sujeto a que tenga sentido:** un resumen de Nómina (montos pagados por período) que se pueda comparar contra la autodeterminación de cuotas del IMSS. Evalúa si esto es viable con los datos que el CFDI de Nómina realmente contiene, o si es una comparación que requeriría datos que el CFDI no trae (dilo con honestidad para no trabajar de más y gastar tokens por una funcionalidad sin viabilidad, como ya se hizo con la limitación de "REP no prueba que el dinero se movió", ROADMAP.md §5.5 D22). Si concluyes que no aplica o no cuadra con los datos disponibles, dilo directamente en vez de forzar un diseño.

## EDICIONES — ESTE REPORTE ES SOLO PRO

Svei definió que este reporte fiscal nuevo es una función de la edición **Pro** (ROADMAP.md §5.2, D10: Lite/Pro/Top = un solo codebase con feature gating por licencia). La edición **Lite** conserva el Excel actual tal como existe hoy (Invoices/Nómina/Pagos, sin este papel de trabajo).

Esto choca en apariencia con D10, que dice que el gating (`editions.py`) NO se implementa antes de F9 — por eso solo se va a hacer el diseño ahora; la implementación real del gating viene en F9. Inclúyelo como punto a resolver en tu entrevista, no lo resuelvas solo.

**Preguntas concretas a hacer a Svei sobre esto:**

- ¿Quiere que el exportador tenga YA un punto de decisión (`if edición == Pro: generar hoja(s) nueva(s) / else: reporte de siempre`) desde que se construya esta función, aunque el sistema completo de licencias (`editions.py`, D10) no exista todavía? Es decir, ¿un gate mínimo/local específico de esta función, no el sistema de licencias completo? Incluye tu sugerencia sincera.

- Durante fase de pruebas y con cualquier persona que se anime a probar el sistema hoy: TODOS ven el reporte nuevo (no hay licencia real corriendo aún) — el gate, si existe, debe defaultear a "mostrar todo" mientras no haya sistema de licencias real, para no bloquear pruebas por accidente y dejar el camino abierto. Una vez que se llegue a F9, aplicar simplemente las reglas.

- Confirmar con Svei: ¿el plan es que este gate provisional se reemplace más adelante (F9) por la consulta real a `editions.py`, sin tener que rediseñar dónde vive la lógica del reporte? Diseña pensando en que ese `if` de hoy sea fácil de conectar al gating real después, no un candado distinto.

**No decidas tú solo si construir el gate ahora o dejarlo para F9** — es justamente lo que tienes que preguntarle a Svei en la entrevista, porque modifica una decisión ya registrada (D10).

## FUENTE DE LA VERDAD: TÚ NO LA TIENES COMPLETA

Svei es contador pero trabaja solo, sin equipo que le confirme reglas de negocio, y tiene la información dispersa en su cabeza. **TU PRIMERA RESPUESTA en esta conversación NO debe ser un diseño** — debe ser una **ENTREVISTA estructurada, por rondas**, para levantar los supuestos antes de proponer nada. Prioriza las preguntas de mayor ambigüedad/impacto primero.

**Ejemplos del tipo de pregunta que deberías hacer** (ajusta y agrega las que hagan falta):

- ¿El "mes" del reporte se ancla a la fecha de emisión/timbrado del CFDI, a la fecha de pago (REP), o depende del tipo de documento (PUE vs PPD)?

- Para "documentos pagados en efectivo menores a $2,000": ¿la fuente de esa regla es un artículo específico que Svei ya conoce y quiere que se cite literal (¿puede subirlo a docs/?), o quiere que se investigue el fundamento exacto?

- ¿Qué significa exactamente "cuadrar" el REP con su PUE/PPD origen para este reporte — solo emparejar por UUID relacionado, o algo más?

- ¿El reporte es por RFC (un solo contribuyente) o debe soportar comparar Emitidas vs Recibidas en la misma vista?

- ¿Notas de crédito con qué UUID de relación deben identificarse — todas las del tipo "E", o solo las relacionadas explícitamente a un CFDI de ingreso?

- Nómina/IMSS: ¿qué dato exacto tiene hoy para comparar (cédula de determinación, SUA, algo manual)? ¿o es una idea a validar si es factible?

- ¿Este reporte reemplaza/complementa las hojas actuales o es una hoja(s) nueva(s) separada(s) (p. ej. "Resumen Fiscal Mensual")?

- ¿Debe ser una sola hoja o varias (ej. una de deducibilidad, otra de nómina/IMSS)? Da tu opinión de contador+UX pero pregunta antes de decidir.

- Las preguntas de edición/gating de la sección anterior (Pro vs Lite, comportamiento durante pruebas).

**Solo después de tener las respuestas** (puede requerir varias rondas), produce el documento de diseño.

## ENTREGABLE ESPERADO (tras la entrevista)

Un documento en el mismo estilo que las secciones ya existentes en ROADMAP.md (para copiar/pegar como nueva sección, ej. futura §17):

1. **Objetivo del/los reporte(s)**, en una frase.

2. **Reglas de negocio CONFIRMADAS por Svei**, cada una con su fuente citada (artículo LISR/CFF/RMF/LIVA/RLIVA o NIF exacta) o marcada "SUPUESTO — validar".

3. **Estructura propuesta:** nombre de cada hoja nueva, columnas, agrupación (mes/año), fórmulas conceptuales en español llano (NO código) — ej. "Total pagado efectivo PUE<$2000 = suma de Total donde MetodoPago=PUE Y FormaPago∈{efectivo} Y Total<2000".

4. **Cómo queda resuelto (o pendiente) el punto de edición Pro/Lite y el gate provisional durante pruebas**, con su propia entrada de decisión D-número.

5. **Preguntas que quedaron abiertas / pendientes de confirmar con Svei.**

6. **Tabla de decisiones** (estilo D-número) para las que sí se cerraron en esta conversación, con fecha y razón — mismo formato que ROADMAP.md §7.

7. **Nota explícita de qué construcción NO se cubre hoy** (para que Sonnet, en la fase siguiente, no invente alcance).

**No propongas nombres de archivos, clases ni funciones Python** — eso es trabajo de la fase de construcción.

---

## Fin del prompt

Cópialo tal cual (desde "ROL Y CONTEXTO") y pégalo en Fable/Opus junto con `PROMPT.md` y `ROADMAP.md` del repo. El modelo debería arrancar con la entrevista.
