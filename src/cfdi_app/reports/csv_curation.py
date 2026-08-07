# --- cfdi_app/reports/csv_curation.py ---
"""Curación de datos para la exportación CSV (F2.9, ROADMAP.md D46-D48).

Correcciones pedidas por el dueño tras probar F2.9 en real (2026-07-25):
formato consistente (fechas ISO, decimales a 2 posiciones, UUID en
mayúsculas, catálogos SAT siempre "código - descripción"), suficiencia
contable (Serie/Folio separados, Fecha de Timbrado, bases de IVA por tasa,
cruce de mejor esfuerzo con el CFDI relacionado) y columnas constantes
"hoisteadas" a un encabezado único en vez de repetirse en cada fila.

PURO a proposito (mismo patron que reports/pt_recibidas.py): sin Qt, sin
csv, sin disco. El parser NO se toca - todo esto son transformaciones sobre
los dicts YA parseados, en la capa CSV unicamente. El Excel/visor no cambian.
"""
from datetime import datetime

from cfdi_app.constants import TIPO_COMPROBANTE_MAP

# --- Reverso de TIPO_COMPROBANTE_MAP (D47): el parser solo guarda la
# etiqueta ("Factura"), nunca el codigo crudo (I/E/P/N/T) - se reconstruye
# aqui, en la capa CSV, sin tocar el parser.
_LABEL_TO_TIPO_CODIGO = {label: code for code, label in TIPO_COMPROBANTE_MAP.items()}

# Campos UUID a normalizar a MAYUSCULAS en cualquier tabla (D47).
UUID_FIELDS = {"UUID", "UUID Relacion", "UUID CFDI", "IdDocumento Relacionado"}

# Campos de "Tipo"/"TipoComprobante" por tabla, para reconstruir "codigo - etiqueta".
TIPO_FIELDS = {"Tipo", "TipoComprobante"}

# Campos monetarios/numericos a formatear con 2 decimales SIEMPRE (D47),
# incluye Tipo De Cambio ("1.0" -> "1.00", ejemplo textual del dueño).
_MONEY_FIELD_HINTS = (
    "SubTotal", "Descuento", "Total", "IVA", "Retenido", "IEPS", "Base",
    "Tipo De Cambio", "TipoCambioP", "MontoTotalPagos", "ImpSaldoAnt",
    "ImpPagado", "ImpSaldoInsoluto", "Sueldos", "Otros Pagos", "Deducciones",
)


def _es_campo_monetario(campo):
    return any(pista in campo for pista in _MONEY_FIELD_HINTS)


def reformat_date(value):
    """DD/MM/YYYY [HH:MM:SS] -> ISO 8601 (D47). Si el valor NO calza con
    ninguno de esos dos formatos (p.ej. ya viene ISO, como "Fecha Inicial
    Pago"/"Fecha Final Pago" de Nomina), se devuelve SIN TOCAR - idempotente
    y seguro para cualquier campo de fecha, conocido o no."""
    if not value:
        return value
    text = str(value).strip()
    for fmt_in, fmt_out in (
        ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"),
        ("%d/%m/%Y", "%Y-%m-%d"),
    ):
        try:
            return datetime.strptime(text, fmt_in).strftime(fmt_out)
        except ValueError:
            continue
    return value


def format_money(value):
    """Numero a 2 decimales, SIEMPRE, como string (D47) - "65.0"/"6.9"/"1.0"
    mezclados con "393.44" era el problema reportado. Valores no numericos
    (None, "", texto) se devuelven sin cambio."""
    if value is None or value == "":
        return value
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return value


def normalize_uuid(value):
    """Mayusculas consistentes (D47): un archivo con UUID en minusculas y
    mayusculas mezcladas rompe cualquier deduplicacion por comparacion
    directa de texto."""
    if not value:
        return value
    return str(value).strip().upper()


def tipo_con_codigo(label):
    """"Factura" -> "I - Factura" (D47/D46 - punto 6). Reconstruye el codigo
    SAT crudo (perdido por el parser, que solo guarda la etiqueta) via el
    reverso de TIPO_COMPROBANTE_MAP. Etiquetas desconocidas se devuelven
    intactas (nunca se inventa un codigo)."""
    if not label:
        return label
    codigo = _LABEL_TO_TIPO_CODIGO.get(str(label))
    if codigo is None:
        return label
    return f"{codigo} - {label}"


def curate_value(field, value):
    """Aplica la transformacion correcta segun el NOMBRE del campo - fechas,
    dinero, UUID, tipo. Un campo que no calza con ninguna regla se devuelve
    intacto (curar NO es inventar)."""
    if field in TIPO_FIELDS:
        return tipo_con_codigo(value)
    if field in UUID_FIELDS:
        return normalize_uuid(value)
    if "Fecha" in field:
        return reformat_date(value)
    if _es_campo_monetario(field):
        return format_money(value)
    return value


def curate_row(row, columns):
    """Copia curada de `row`, restringida a `columns` (en ese orden), con
    curate_value() aplicado campo por campo."""
    return {col: curate_value(col, row.get(col)) for col in columns}


# --- Bases de IVA por tasa (D48/punto 10) -----------------------------------

# c_TasaOCuota -> nombre de columna de base (mismo vocabulario que ya usa
# pagos_parser_20.py para Pagos: "IVA 16 Base"/"IVA 8 Base"/"IVA Cero Base").
_TASA_A_COLUMNA_BASE = {
    "0.160000": "IVA 16 Base",
    "0.080000": "IVA 8 Base",
    "0.000000": "IVA Cero Base",
}
IVA_BASE_COLUMNS = list(_TASA_A_COLUMNA_BASE.values()) + ["IVA Exenta Base"]


def compute_iva_bases(conceptos_detalle):
    """Suma la Base de IVA (Impuesto SAT "002") por tasa, a partir de
    ConceptosDetalle (D25/F2.6 - ya capturado por el parser, campo interno,
    NUNCA expuesto en Excel/visor). Cuando el parser NO conoce la tasa
    exacta o el concepto es Exento (TipoFactor="Exento", sin TasaOCuota),
    se suma a "IVA Exenta Base". Un concepto SIN nodo Impuestos (ObjetoImp
    "01" - no objeto de impuesto) no aporta a ninguna base.

    Sin bases de IVA por tasa no se puede armar DIOT ni validar la
    determinacion de IVA (feedback real del dueño, D48)."""
    bases = {col: 0.0 for col in IVA_BASE_COLUMNS}
    for concepto in conceptos_detalle or []:
        traslados = (concepto.get("Impuestos") or {}).get("Traslados") or []
        for traslado in traslados:
            if traslado.get("Impuesto") != "002":  # 002 = IVA
                continue
            base = _a_float(traslado.get("Base"))
            if traslado.get("TipoFactor") == "Exento":
                bases["IVA Exenta Base"] += base
                continue
            columna = _TASA_A_COLUMNA_BASE.get(traslado.get("TasaOCuota"))
            if columna:
                bases[columna] += base
    return bases


def _a_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# --- Cruce de mejor esfuerzo con el CFDI relacionado (D48/punto 11) --------

def build_uuid_index(full_batch_rows):
    """{UUID en MAYUSCULAS -> row} de TODO el lote (no solo lo filtrado en
    pantalla) - la mejor oportunidad de resolver el cruce, independiente del
    filtro activo del visor en ese momento."""
    indice = {}
    for row in full_batch_rows or []:
        uuid = str(row.get("UUID", "")).strip().upper()
        if uuid:
            indice[uuid] = row
    return indice


def related_document_fields(related_uuid, uuid_index):
    """(Serie, Folio, Fecha) del CFDI referenciado por `related_uuid`, SOLO
    si ese documento tambien esta en `uuid_index` (mismo lote). El SAT NO
    incluye Serie/Folio/Fecha del relacionado en el XML que lo referencia -
    verificado en cfdv40.xsd: CfdiRelacionado solo trae UUID (D48) - asi que
    fuera del lote simplemente no hay forma de saberlo; se devuelven cadenas
    vacias, nunca un dato inventado."""
    if not related_uuid:
        return "", "", ""
    original = uuid_index.get(str(related_uuid).strip().upper())
    if original is None:
        return "", "", ""
    return (
        original.get("Serie") or "",
        original.get("Folio") or "",
        reformat_date(original.get("Fecha Emision")) or "",
    )


# --- Columnas constantes -> encabezado unico (D46/punto 1) ------------------

def hoist_constant_columns(rows, columns, min_rows=2):
    """Separa `columns` en (constantes, resto) segun si TODAS las filas
    comparten el MISMO valor para esa columna. Deteccion GENERICA - no hay
    una lista fija de "campos RFC" - asi que invierte solo entre
    Emitidas/Recibidas/Nomina sin logica de direccion duplicada (D46).

    Con menos de `min_rows` filas no se hoistea nada (evita vaciar la tabla
    completa en un lote de una sola fila, donde TODO es "constante" por
    definicion).

    Devuelve (constantes: dict, columnas_restantes: list, filas_restantes:
    list de dicts). El ORDEN de columnas_restantes respeta el de `columns`.
    """
    if len(rows) < min_rows:
        return {}, list(columns), list(rows)

    constantes = {}
    restantes = []
    for col in columns:
        valores = {row.get(col) for row in rows}
        if len(valores) == 1:
            constantes[col] = next(iter(valores))
        else:
            restantes.append(col)

    filas_restantes = [{col: row.get(col) for col in restantes} for row in rows]
    return constantes, restantes, filas_restantes


def build_preamble_lines(constant_fields):
    """Lineas '# Campo: valor' para el encabezado unico (D46). Formato
    comentario: Excel/pandas las saltan solas (comment='#') y el archivo
    sigue siendo CSV valido para casi cualquier herramienta, no solo para
    una IA leyendo texto crudo."""
    return [f"# {campo}: {valor}" for campo, valor in constant_fields.items()]


# --- Enriquecimiento (D48): agrega campos derivados ANTES de curar/elegir --

def enrich_invoice_row(row, uuid_index):
    """Copia de `row` con bases de IVA por tasa (#10) y el cruce de mejor
    esfuerzo con el CFDI relacionado (#11) agregados. Campos DERIVADOS - no
    vienen del parser, se calculan aqui cada vez que se exporta."""
    enriched = dict(row)
    enriched.update(compute_iva_bases(row.get("ConceptosDetalle")))
    serie_rel, folio_rel, fecha_rel = related_document_fields(
        row.get("UUID Relacion"), uuid_index)
    enriched["Serie Relacionada"] = serie_rel
    enriched["Folio Relacionada"] = folio_rel
    enriched["Fecha Relacionada"] = fecha_rel
    return enriched


def enrich_pagos_row(row, uuid_index):
    """Copia de `row` con SOLO la Fecha del documento relacionado agregada -
    Serie/Folio Relacionado YA vienen nativos del parser para Pagos (via
    pago20:DoctoRelacionado), a diferencia de Facturas donde el SAT no los
    incluye (D48)."""
    enriched = dict(row)
    _serie, _folio, fecha_rel = related_document_fields(
        row.get("IdDocumento Relacionado"), uuid_index)
    enriched["Fecha Relacionada"] = fecha_rel
    return enriched


# --- Columnas curadas por pestaña (D46-D48) --------------------------------
# Construidas sobre las columnas ya curadas del visor (D18), + las adiciones
# de suficiencia de esta ronda de correcciones. Independientes de
# INVOICE_COLUMN_ORDER/etc. (esas son del Excel/visor; estas son SOLO CSV).

CSV_INVOICE_COLUMNS = [
    "Factura", "Serie", "Folio", "Tipo", "Fecha Emision", "Fecha Timbrado",
    "RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
    "UsoCFDI", "LugarDeExpedicion",
    "SubTotal", "Descuento",
    "IVA 16 Base", "IVA 8 Base", "IVA Cero Base", "IVA Exenta Base",
    "IVA 16%", "Retenido IVA", "Retenido ISR", "Total IEPS", "Total",
    "Moneda", "Tipo De Cambio", "FormaDePago", "Metodo de Pago",
    "Conceptos", "UUID", "UUID Relacion",
    "Serie Relacionada", "Folio Relacionada", "Fecha Relacionada",
]

CSV_NOMINA_COLUMNS = [
    "Factura", "Tipo", "Tipo Nomina", "Fecha Inicial Pago", "Fecha Final Pago",
    "RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
    "CURP", "NSS", "SubTotal", "Total Sueldos", "Total Otros Pagos",
    "Total Deducciones", "Total", "Periodicidad Pago",
    "Registro Patronal", "Conceptos", "UUID",
]

CSV_PAGOS_COLUMNS = [
    "Serie CFDI", "Folio CFDI", "TipoComprobante", "Fecha Emision",
    "RFC Emisor CFDI", "Nombre Emisor CFDI",
    "RFC Receptor CFDI", "Nombre Receptor CFDI",
    "FechaPago", "FormaDePagoP", "MontoTotalPagos",
    "IVA 16 Base", "IVA 8 Base", "IVA Cero Base", "IVA Excento Base",
    "Serie Relacionada", "Folio Relacionado", "Fecha Relacionada",
    "NumParcialidad", "ImpSaldoAnt", "ImpPagado", "ImpSaldoInsoluto",
    "NumOperacion", "UUID CFDI",
]

CSV_COLUMNS_BY_TAB = {
    "invoice_data": CSV_INVOICE_COLUMNS,
    "nomina_data": CSV_NOMINA_COLUMNS,
    "pagos_data": CSV_PAGOS_COLUMNS,
}

# Columnas de suficiencia (D48) a AGREGAR incluso en modo "Todas las
# columnas" - son datos nuevos, no un recorte, asi que ambos modos las
# incluyen (core.py las anexa via dedup a la lista completa del Excel).
EXTRA_INVOICE_COLUMNS = (
    ["Serie", "Folio", "Fecha Timbrado"] + IVA_BASE_COLUMNS +
    ["Serie Relacionada", "Folio Relacionada", "Fecha Relacionada"]
)
EXTRA_PAGOS_COLUMNS = ["Fecha Relacionada"]
