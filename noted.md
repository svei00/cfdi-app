# Notas de entrega — Desglose de conceptos y combustible de monedero (F2.10)

Actualizado: 2026-10-28. Estado: en `main`, probado por el dueño en su equipo
("los resultados se ven bien"). Detalle técnico: `docs/design-f2.10-desglose-conceptos.md`.

## 1. Para qué se hizo

Las facturas de Edenred (`ASE930924SS7`, gasolina) no aparecían como gasolina:
el CFDI solo trae la **comisión** (~$1,000) y la gasolina real vive dentro de un
complemento (Estado de Cuenta de Combustibles) que la app no leía. En los dos
estados de cuenta de muestra, eso eran **$28,185.69** (jun-2026) y
**$40,447.09** (ago-2026) con IVA que no se veían. Lo mismo se necesitaba para
facturas con muchos conceptos (Walmart, Home Depot): ver el desglose por XML,
mes, ejercicio y proveedor.

## 2. Mejoras entregadas

### Lectura y reportes
| # | Mejora | Dónde |
|---|---|---|
| 1 | La app **lee el complemento de combustible** (cada carga: tarjeta, estación, litros, precio, IVA). Salida de los XML anteriores idéntica a la de antes | Automático al procesar |
| 2 | **Reporte Excel del lote**: Detalle, Por proveedor, Por mes, Por ejercicio, Por concepto, Combustible, IVA y Cuadre. Totales que suman solo lo filtrado | Inicio → Reportes → «Desglose de conceptos…» |
| 3 | **Hoja IVA**: el IVA de la factura y el del combustible siempre en columnas separadas, con bases por tasa (16 %, 8 %, 0 %, exento) | En el Excel del desglose |
| 4 | **Hoja Cuadre**: avisa qué CFDI no cuadran con sus totales | En el Excel del desglose |
| 5 | **Desglose de un solo XML**: líneas, totales y semáforo de cuadre; se puede exportar | Clic derecho en una factura → «Ver desglose de este XML» |
| 6 | **Visor «Desglose del lote…»**: árbol Proveedor (RFC) → Factura → conceptos, con caja de búsqueda (RFC, razón social, factura, UUID, concepto, tarjeta, estación; y montos como `total>=5000`). Doble clic abre el XML. Exporta lo filtrado | Botón en el Administrador de Bóveda |
| 7 | **Filtro de proveedor** por RFC o razón social (sin acentos, varias palabras), con «Todos los proveedores» siempre disponible | Diálogo del desglose |
| 8 | **Impuestos locales** (ISH de hospedaje): aparecen como línea propia para que las sumas cuadren con el CFDI | En el desglose |

### Experiencia de uso (a petición del dueño tras probar)
| # | Mejora |
|---|---|
| 9 | Reportes ya **no se queda mudo** sin periodo cargado: muestra un aviso y, al pulsar, explica qué hacer |
| 10 | La app **recuerda el último periodo procesado**; desde Reportes ofrece cargarlo y **abre el desglose sola** al terminar |
| 11 | El botón «Desglose del lote…» está en la propia Bóveda, donde se trabaja |

### Papel de trabajo fiscal (Recibidas)
| # | Mejora |
|---|---|
| 12 | Columnas nuevas: **Combustible monedero**, **IVA combustible monedero**, **IVA monedero acreditable** y «IVA acreditable estimado + monedero» (fórmula de Excel). Ninguna columna anterior cambió |
| 13 | Detalle por factura: cargas, litros, importe, IVA, estatus con color y **mes de timbrado** |
| 14 | Alerta de **posible duplicado**: una factura de la gasolinera que repite una carga del monedero |
| 15 | Hoja Fundamentos con las citas de la RMF 2026 regla 3.3.1.7 |

## 3. Qué está verificado y qué no (importante para el cliente)

- **Verificado con el texto oficial (regla 3.3.1.7):** el CFDI comprueba la
  comisión y el complemento comprueba el combustible; el acreditamiento procede
  «hasta que cuente con el CFDI y el complemento… y hasta por el monto que
  ampare el complemento».
- **Pendiente F2:** que pagar con monedero cuente como pago bancarizado
  (falta el texto de la LISR art. 27 fr. III, párr. 2).
- **Pendiente F4:** requisito del permiso de la Ley de Hidrocarburos (la regla
  no lo menciona; el complemento no trae número de permiso).
- **Efecto hoy:** el IVA del monedero **se muestra pero no se suma** al IVA
  acreditable (queda en 0, semáforo ámbar) hasta cerrar F2 y F4. Con dos citas
  más se pasa a verde.
- El texto de la regla lo copió el dueño de la página del SAT: **cotejar con el
  DOF** antes de usarlo en un dictamen.
- El tope de deducción de automóviles (LISR 36) y el IEPS **no** se calculan.

## 4. Retroalimentación que se necesita del cliente

Marcar cada punto con la respuesta y la fecha.

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | **¿En qué mes se acredita el IVA del monedero?** Los dos estados de cuenta de muestra se emiten el último día del mes y se timbran al siguiente (30/06 → 01/07 y 31/08 → 01/09). Hoy se usa el mes de emisión. ¿Emisión o timbrado? (criterio del contador) | |
| 2 | ¿Tienen el texto de **LISR 27-III párr. 2** y algo sobre el **permiso de Hidrocarburos** para cerrar F2 y F4? | |
| 3 | ¿Quieren que el IVA del monedero **se sume ya** al acreditable (bajo su responsabilidad) o esperar a cerrar F2 y F4? | |
| 4 | ¿Las hojas del Excel (Detalle, resúmenes, Combustible, IVA, Cuadre) cubren lo que necesitan? ¿Falta alguna columna o corte? | |
| 5 | ¿El desglose sirve con **Walmart / Home Depot** u otros? Se necesitan 1–2 XML reales (se anonimizan) de facturas con muchos conceptos para probar | |
| 6 | ¿Tienen CFDI **3.3** o estados de cuenta de años anteriores? Hoy el CFDI 3.3 **no** se desglosa por concepto | |
| 7 | ¿Cuántos CFDI suelen cargar a la vez? (si el visor del lote se siente lento, avisar el número) | |
| 8 | ¿La alerta de **posible duplicado** con la gasolinera es útil o estorba? | |
| 9 | ¿Qué formato necesitan para el **material de análisis** del IVA (el que se mencionó)? ¿Gráficas, tablas, otro Excel? | |
| 10 | Comentarios libres sobre uso: lo que confunde, lo que falta, lo que sobra | |

## 5. Pendientes técnicos (no bloquean al cliente)

- Subir a GitHub los tags de respaldo `pre-f2.10-ecc` y `pre-f2.10-etapa4`
  (no se han podido subir desde la sesión en la nube).
- Búsqueda de texto libre sobre **todo** lo histórico sin cargar el lote: llega
  con la base de datos (F5). Hoy se busca solo dentro del lote cargado.
- Detalle por concepto para CFDI 3.3 (el parser 3.3 no lo produce).
- Estatus SAT (vigente/cancelado): fase F7, no existe todavía.
- Probar las ventanas nuevas en más equipos: las pruebas de interfaz solo se
  corrieron en el equipo del dueño.
