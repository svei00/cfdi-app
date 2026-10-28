# --- cfdi_app/exporters/pt_exporter.py ---
"""Escritura de las hojas del Papel de Trabajo (F2.8, ROADMAP §17.4) en el
MISMO libro de Excel que ya arma excel_exporter. Etapa 1: PT-Recibidas
(resumen + detalle). Consume la capa PURA reports/pt_recibidas.py; aqui solo
vive openpyxl (celdas, colores, formulas vivas).

Capacidad NUEVA de esta etapa (ROADMAP §17.4.2/D34): las hojas PT llevan
FORMULAS reales de Excel (SUMIF -> se muestra como SUMAR.SI en Excel en
español), no valores congelados - la columna manual "Conciliado banco"
recalcula sus sumas en vivo cuando el usuario marca.
"""
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from cfdi_app.reports import pt_recibidas as pt

# Nombres de hoja (cortos; Excel limita a 31 chars).
HOJA_RESUMEN = "PT-Recibidas"
HOJA_DETALLE = "PT-Recibidas Detalle"
HOJA_FUNDAMENTOS = "Fundamentos"

# Citas legales (ROADMAP §17.2, verificadas CON LEY EN MANO - regla §13.1/§17:
# ningun articulo se cita de memoria). La regla RMF del plazo del REP se
# ubico y verifico en RMF_2026-DOF-28122025.md (regla 2.7.1.32) durante esta
# construccion (2026-07-25).
_FUNDAMENTOS = [
    ("R1", "Pagos cuyo monto exceda de $2,000 deben pagarse con forma "
           "bancarizada para ser deducibles. Se compara el monto total con "
           "IVA incluido.", "LISR art. 27, fr. III (PM); art. 147, fr. IV (PF)"),
    ("R2", "Combustibles: el pago debe ser bancarizado SIEMPRE, sin importar "
           "el monto.", "LISR art. 27, fr. III, párr. 2 (DOF 12-11-2021)"),
    ("R3", "El IVA es acreditable solo cuando fue efectivamente pagado en el "
           "mes.", "LIVA art. 5, fr. III"),
    ("R4", "Se considera efectivamente pagado cuando la obligación se extingue "
           "(incluye anticipos; cheque hasta su cobro).", "LIVA art. 1o.-B"),
    ("R5", "Devoluciones, descuentos y bonificaciones (notas de crédito) se "
           "netean en el mes en que ocurren, con restitución del IVA.",
     "LIVA art. 7"),
    ("R6", "Forma de pago bancarizada según catálogo c_FormaPago: "
           "02, 03, 04, 05, 06, 28, 29 = Sí; 01 y demás = No; 99 = por definir.",
     "Anexo 20, catálogo c_FormaPago"),
    ("R7", "Un CFDI PPD se considera pagado solo con su Complemento de Pago "
           "(REP); el mes lo da la FechaPago del REP. El REP se emite a más "
           "tardar el 5o día natural del mes siguiente al pago.",
     "CFF art. 29-A; RMF 2026 regla 2.7.1.32 (DOF 28-12-2025)"),
    ("R8", "Combustible se identifica por concepto vía ClaveProdServ de la "
           "familia 1510.", "Catálogo c_ClaveProdServ, familia 1510"),
    ("XAXX", "CFDI expedido al RFC genérico XAXX010101000 (público en general): "
             "NO deducible e IVA NO acreditable.",
     "CFF art. 29-A, fr. IV; LISR art. 27, fr. III; LIVA art. 5, fr. II"),
    ("Nota", "La forma 06 'Dinero electrónico' se clasifica como bancarizada "
             "por catálogo, aunque LISR 27-III no la nombre textualmente.",
     "Anexo 20, catálogo c_FormaPago"),
]

_DISCLAIMER = (
    "Proyección estimada con base en los CFDI procesados. NO constituye "
    "cálculo de impuestos ni sustituye el criterio profesional. El uso y la "
    "interpretación de este papel de trabajo son responsabilidad del "
    "usuario/contador. La columna 'Conciliado banco' es manual: el CFDI "
    "declara la forma de pago, solo el estado de cuenta bancario la confirma."
)

_NOTAS_ECC = [
    "Mientras algún fundamento F1–F4 esté pendiente, las cifras del monedero "
    "se muestran pero NO se suman al IVA acreditable (columna 'IVA monedero "
    "acreditable' = 0).",
    "El monedero se ancla al mes de EMISIÓN del CFDI (decisión del dueño). La "
    "regla 3.3.1.7 permite deducir y acreditar 'hasta que' se cuente con el "
    "CFDI y el complemento: revise la columna 'Mes de timbrado (ECC)', "
    "resaltada cuando el timbrado cae en otro mes que la emisión.",
    "No se calcula el tope de deducción de automóviles (LISR art. 36) ni el "
    "IEPS del combustible.",
    "'Posible duplicado monedero' es solo una advertencia: la regla 3.3.1.7 "
    "dice que las estaciones no deben emitir CFDI por operaciones con "
    "monedero; una factura de estación por el mismo importe puede duplicar el "
    "gasto.",
]

# Colores de semaforo = los estandar de Excel (Bueno/Malo/Neutral).
_FILL_VERDE = PatternFill("solid", fgColor="C6EFCE")
_FILL_ROJO = PatternFill("solid", fgColor="FFC7CE")
_FILL_AMBAR = PatternFill("solid", fgColor="FFEB9C")
_FONT_VERDE = Font(color="006100")
_FONT_ROJO = Font(color="9C0006")
_FONT_AMBAR = Font(color="9C6500")

_SEMAFORO = {
    pt.NIVEL_VERDE: (_FILL_VERDE, _FONT_VERDE),
    pt.NIVEL_ROJO: (_FILL_ROJO, _FONT_ROJO),
    pt.NIVEL_AMBAR: (_FILL_AMBAR, _FONT_AMBAR),
}

_FILL_HEADER = PatternFill("solid", fgColor="1F4E78")
_FONT_HEADER = Font(color="FFFFFF", bold=True)
_MONEDA = '#,##0.00'
_MARCA_CONCILIADO = "✓"

# Columnas del resumen: (clave en la fila pura, encabezado visible).
_COLS_RESUMEN = [
    ("mes", "Mes"),
    ("pue_bancarizado", "PUE bancarizado"),
    ("pue_efectivo_deducible", "PUE efectivo deducible (≤$2,000)"),
    ("pue_efectivo_no_deducible", "PUE efectivo NO deducible (>$2,000)"),
    ("combustible_no_deducible", "Combustible no deducible"),
    ("ppd_facturado", "PPD facturado"),
    ("ppd_pagado", "PPD pagado (vía REP)"),
    ("ppd_provisionado", "PPD provisionado"),
    ("nc_recibidas", "NC recibidas"),
    ("subtotal_neto", "SubTotal neto"),
    ("iva_neto", "IVA neto"),
    ("total_neto", "Total neto"),
    ("iva_acreditable_estimado", "IVA acreditable estimado"),
    # F2.10 etapa 4 (D58): el monedero va SOLO en columnas nuevas, al final.
    ("combustible_monedero", "Combustible monedero"),
    ("iva_combustible_monedero", "IVA combustible monedero"),
    ("iva_monedero_acreditable", "IVA monedero acreditable"),
]
# Columna de FORMULA VIVA (D34/D58): suma las dos columnas a la vista, nunca
# un numero ya sumado. Se escribe a continuacion de las de _COLS_RESUMEN.
_TITULO_IVA_CON_MONEDERO = "IVA acreditable estimado + monedero"
_CLAVES_MONEDERO_RESUMEN = ("combustible_monedero", "iva_combustible_monedero",
                            "iva_monedero_acreditable")
_NOTA_PENDIENTE = " (pendiente de verificar fundamento)"

# Columnas del detalle: (clave en el registro clasificado, encabezado, moneda?).
_COLS_DETALLE = [
    ("mes_txt", "Mes", False),
    ("uuid", "UUID", False),
    ("fecha_emision", "Fecha", False),
    ("rfc_emisor", "RFC Emisor", False),
    ("nombre_emisor", "Nombre Emisor", False),
    ("metodo", "Método", False),
    ("forma_efectiva", "Forma efectiva", False),
    ("combustible_txt", "¿Combustible?", False),
    ("bancarizada_txt", "¿Bancarizado?", False),
    ("rep_txt", "¿Tiene REP?", False),
    ("subtotal_mxn", "SubTotal MXN", True),
    ("iva_mxn", "IVA MXN", True),
    ("total_mxn", "Total MXN", True),
    ("estatus", "Estatus", False),
    ("conciliado", "Conciliado banco", False),
    # F2.10 etapa 4: monedero, al final para no mover las columnas de arriba.
    ("ecc_cargas", "Cargas ECC", False),
    ("ecc_litros", "Litros ECC", False),
    ("ecc_importe_mxn", "Importe ECC MXN", True),
    ("ecc_iva_mxn", "IVA ECC MXN", True),
    ("ecc_estatus", "Estatus ECC", False),
    ("mes_timbrado_txt", "Mes de timbrado (ECC)", False),
    ("posible_duplicado_monedero", "Posible duplicado monedero", False),
]
_COL_ESTATUS_ECC = 20  # posicion 1-indexed de "Estatus ECC" en el detalle
_COL_TOTAL_MXN = 13   # posicion 1-indexed de "Total MXN" en el detalle
_COL_IVA_MXN = 12
_COL_CONCILIADO = 15  # posicion 1-indexed de "Conciliado banco"


def _si_no(valor):
    return "Sí" if valor else "No"


def _estilo_encabezado(ws, num_cols):
    for col in range(1, num_cols + 1):
        celda = ws.cell(row=1, column=col)
        celda.fill = _FILL_HEADER
        celda.font = _FONT_HEADER
        celda.alignment = Alignment(horizontal="center", vertical="center",
                                    wrap_text=True)
    ws.freeze_panes = "A2"  # encabezados siempre visibles al hacer scroll


def _autoajustar(ws, num_cols, ancho_max=48):
    for col in range(1, num_cols + 1):
        letra = get_column_letter(col)
        largo = max((len(str(c.value)) for c in ws[letra] if c.value is not None),
                    default=10)
        ws.column_dimensions[letra].width = min(largo + 2, ancho_max)


def _escribir_resumen(ws, resumen):
    n_pure = len(_COLS_RESUMEN)
    n_cols = n_pure + 1  # + columna de formula viva
    claves = [c for c, _ in _COLS_RESUMEN]
    letra_iva = get_column_letter(claves.index("iva_acreditable_estimado") + 1)
    letra_mon = get_column_letter(claves.index("iva_monedero_acreditable") + 1)

    titulos = [titulo for _, titulo in _COLS_RESUMEN]
    pendiente = not pt.ecc_fundamentado()
    if pendiente:
        # Solo la columna que depende de la verificacion lleva la nota.
        i = claves.index("iva_monedero_acreditable")
        titulos[i] += _NOTA_PENDIENTE
    ws.append(titulos + [_TITULO_IVA_CON_MONEDERO])
    _estilo_encabezado(ws, n_cols)
    if pendiente:
        for clave in _CLAVES_MONEDERO_RESUMEN:
            celda = ws.cell(row=1, column=claves.index(clave) + 1)
            celda.fill = PatternFill("solid", fgColor="9C6500")

    for fila in resumen:
        r = ws.max_row + 1
        ws.append([fila[clave] for clave in claves]
                  + [f"={letra_iva}{r}+{letra_mon}{r}"])

    # Formato de moneda a todas las columnas numericas (todas menos "Mes").
    for row in range(2, ws.max_row + 1):
        for col in range(2, n_cols + 1):
            ws.cell(row=row, column=col).number_format = _MONEDA

    # Fila de totales con SUM vivo (cuadre §17.9.1 visible en el propio Excel).
    if resumen:
        total_row = ws.max_row + 1
        ws.cell(row=total_row, column=1, value="TOTAL").font = Font(bold=True)
        for col in range(2, n_cols + 1):
            letra = get_column_letter(col)
            celda = ws.cell(row=total_row, column=col,
                            value=f"=SUM({letra}2:{letra}{ws.max_row})")
            celda.number_format = _MONEDA
            celda.font = Font(bold=True)

    _autoajustar(ws, n_cols)


def _escribir_detalle(ws, detalle):
    ws.append([titulo for _, titulo, _ in _COLS_DETALLE])
    _estilo_encabezado(ws, len(_COLS_DETALLE))

    for reg in detalle:
        vista = {
            "mes_txt": pt._mes_clave(reg["mes"]),
            "uuid": reg["uuid"],
            "fecha_emision": reg["fecha_emision"],
            "rfc_emisor": reg["rfc_emisor"],
            "nombre_emisor": reg["nombre_emisor"],
            "metodo": reg["metodo"],
            "forma_efectiva": reg["forma_efectiva"],
            "combustible_txt": _si_no(reg["es_combustible"]),
            "bancarizada_txt": _si_no(reg["es_bancarizada"]),
            "rep_txt": _si_no(reg["tiene_rep"]),
            "subtotal_mxn": reg["subtotal_mxn"],
            "iva_mxn": reg["iva_mxn"],
            "total_mxn": reg["total_mxn"],
            "estatus": reg["estatus"],
            "conciliado": "",  # el usuario marca ✓ a mano
            "ecc_cargas": reg["ecc_cargas"],
            "ecc_litros": reg["ecc_litros"],
            "ecc_importe_mxn": reg["ecc_importe_mxn"],
            "ecc_iva_mxn": reg["ecc_iva_mxn"],
            "ecc_estatus": reg["ecc_estatus"],
            "mes_timbrado_txt": (pt._mes_clave(reg["mes_timbrado"])
                                 if reg["ecc_cargas"] else ""),
            "posible_duplicado_monedero": reg["posible_duplicado_monedero"],
        }
        ws.append([vista[clave] for clave, _, _ in _COLS_DETALLE])

        fila = ws.max_row
        # Semaforo: colorear la celda de Estatus segun el nivel calculado.
        fill, font = _SEMAFORO[reg["nivel"]]
        celda_estatus = ws.cell(row=fila, column=14)
        celda_estatus.fill = fill
        celda_estatus.font = font
        if reg["ecc_nivel"]:
            fill_e, font_e = _SEMAFORO[reg["ecc_nivel"]]
            celda_ecc = ws.cell(row=fila, column=_COL_ESTATUS_ECC)
            celda_ecc.fill = fill_e
            celda_ecc.font = font_e
        if reg["ecc_timbrado_otro_mes"]:  # F3: el contador debe verlo
            ws.cell(row=fila, column=_COL_ESTATUS_ECC + 1).fill = _FILL_AMBAR
        # Formato de moneda en las columnas de importe.
        for col, _, es_moneda in [(i + 1, t, m) for i, (_, t, m) in enumerate(_COLS_DETALLE)]:
            if es_moneda:
                ws.cell(row=fila, column=col).number_format = _MONEDA

    if detalle:
        _bloque_conciliacion(ws, primera=2, ultima=ws.max_row)
        _validacion_marca(ws, primera=2, ultima=ws.max_row)

    _autoajustar(ws, len(_COLS_DETALLE))


def _bloque_conciliacion(ws, primera, ultima):
    """Formulas VIVAS (§17.9.6): al marcar ✓ en 'Conciliado banco', estas
    sumas recalculan solas en Excel. SUMIF se muestra como SUMAR.SI en un
    Excel en español (el formato xlsx guarda el nombre canonico en ingles)."""
    col_total = get_column_letter(_COL_TOTAL_MXN)
    col_iva = get_column_letter(_COL_IVA_MXN)
    col_marca = get_column_letter(_COL_CONCILIADO)
    rango_total = f"{col_total}{primera}:{col_total}{ultima}"
    rango_iva = f"{col_iva}{primera}:{col_iva}{ultima}"
    rango_marca = f"{col_marca}{primera}:{col_marca}{ultima}"

    base = ultima + 2
    etiquetas_formulas = [
        ("Total conciliado (✓):",
         f'=SUMIF({rango_marca},"{_MARCA_CONCILIADO}",{rango_total})'),
        ("Total sin conciliar:",
         f'=SUM({rango_total})-SUMIF({rango_marca},"{_MARCA_CONCILIADO}",{rango_total})'),
        ("IVA conciliado (✓):",
         f'=SUMIF({rango_marca},"{_MARCA_CONCILIADO}",{rango_iva})'),
    ]
    for i, (etiqueta, formula) in enumerate(etiquetas_formulas):
        r = base + i
        ws.cell(row=r, column=_COL_TOTAL_MXN - 1, value=etiqueta).font = Font(bold=True)
        celda = ws.cell(row=r, column=_COL_TOTAL_MXN, value=formula)
        celda.number_format = _MONEDA
        celda.font = Font(bold=True)


def _validacion_marca(ws, primera, ultima):
    """Dropdown con ✓ en la columna Conciliado banco: marcar es un clic, no
    escribir un caracter raro a mano."""
    col_marca = get_column_letter(_COL_CONCILIADO)
    dv = DataValidation(type="list", formula1=f'"{_MARCA_CONCILIADO}"',
                        allow_blank=True)
    dv.add(f"{col_marca}{primera}:{col_marca}{ultima}")
    ws.add_data_validation(dv)


def _escribir_fundamentos(ws):
    """Hoja de citas legales verificadas + disclaimer (§17.4.5). Cada regla del
    PT tiene aqui su fundamento (ley, articulo, fraccion) - obligacion del
    despacho: citar el fundamento en toda conclusion fiscal."""
    ws.append(["Fundamentos legales del Papel de Trabajo"])
    ws.cell(row=1, column=1).font = Font(bold=True, size=14)

    ws.append([])
    ws.append(["Regla", "Criterio aplicado", "Fundamento"])
    encabezado_fila = ws.max_row
    for col in range(1, 4):
        celda = ws.cell(row=encabezado_fila, column=col)
        celda.fill = _FILL_HEADER
        celda.font = _FONT_HEADER
        celda.alignment = Alignment(horizontal="center", vertical="center")

    for regla, criterio, fundamento in _FUNDAMENTOS:
        ws.append([regla, criterio, fundamento])
        fila = ws.max_row
        ws.cell(row=fila, column=1).font = Font(bold=True)
        ws.cell(row=fila, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=fila, column=3).alignment = Alignment(wrap_text=True, vertical="top")

    # F2.10 etapa 4: combustible con monedero electronico. La cita se muestra
    # tal cual esta verificada; si no, el texto literal de pendiente.
    ws.append([])
    ws.append(["Combustible con monedero electrónico (F2.10 etapa 4)"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    for fid, criterio, cita in pt.FUNDAMENTOS_ECC:
        ws.append([fid, criterio,
                   cita or "PENDIENTE DE VERIFICAR — no se cita de memoria "
                           "(F2.10 diseño §8.1)"])
        fila = ws.max_row
        ws.cell(row=fila, column=1).font = Font(bold=True)
        for col in (2, 3):
            ws.cell(row=fila, column=col).alignment = Alignment(
                wrap_text=True, vertical="top")
        if cita is None:
            ws.cell(row=fila, column=3).fill = _FILL_AMBAR
    for nota in _NOTAS_ECC:
        ws.append(["Nota", nota])
        fila = ws.max_row
        ws.cell(row=fila, column=1).font = Font(bold=True)
        ws.cell(row=fila, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=3)

    ws.append([])
    fila_disc = ws.max_row + 1
    ws.cell(row=fila_disc, column=1, value="Aviso:").font = Font(bold=True, color="9C0006")
    celda_disc = ws.cell(row=fila_disc, column=2, value=_DISCLAIMER)
    celda_disc.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=fila_disc, start_column=2, end_row=fila_disc, end_column=3)

    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 70
    ws.column_dimensions["C"].width = 90


def escribir_hojas_pt_recibidas(workbook, invoice_data_list, pagos_data_list):
    """Agrega las hojas PT-Recibidas (resumen + detalle + Fundamentos) a un
    workbook openpyxl YA abierto por excel_exporter. Las notas de credito
    (tipo E) viajan dentro de invoice_data_list; los REP en pagos_data_list. Si
    no hay nada recibido, no crea hojas (no ensucia el libro con hojas vacias)."""
    parsed = list(invoice_data_list or []) + list(pagos_data_list or [])
    rfc_sujeto = pt.determinar_rfc_sujeto(parsed)

    detalle = pt.construir_detalle(parsed, rfc_sujeto, pagos_data_list or [])
    if not detalle:
        return False  # el lote no tiene facturas recibidas para este sujeto

    resumen = pt.construir_resumen_mensual(parsed, rfc_sujeto, pagos_data_list or [])
    _escribir_resumen(workbook.create_sheet(HOJA_RESUMEN), resumen)
    _escribir_detalle(workbook.create_sheet(HOJA_DETALLE), detalle)
    _escribir_fundamentos(workbook.create_sheet(HOJA_FUNDAMENTOS))
    return True
