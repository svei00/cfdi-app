# --- cfdi_app/reports/pt_recibidas.py ---
"""Papel de Trabajo — RECIBIDAS (F2.8 etapa 1, ROADMAP §17.4).

Analisis de egresos por flujo de efectivo: clasifica cada CFDI RECIBIDO
(donde el cliente es el receptor) segun deducibilidad e IVA acreditable, y
arma el resumen mensual. Todo PURO y probable sin Excel.

Reglas y fundamentos (ROADMAP §17.2 + reglas del despacho de Ivan):
  R1  Pagos > $2,000 deben ser bancarizados para deducir . LISR 27-III (PM),
      147-IV (PF).
  R2  Combustible: bancarizado SIEMPRE, sin umbral . LISR 27-III parr. 2.
  R3  IVA acreditable solo cuando efectivamente pagado en el mes . LIVA 5-III.
  R6  Bancarizado por catalogo c_FormaPago: Si = 02,03,04,05,06,28,29;
      No = 01 y resto; 99 = indeterminado . docs/catalogos_filtrados.md.
  R7  PPD se considera pagado solo con su REP; el mes lo da FechaPago; la
      forma real es FormaDePagoP del REP . CFF/Anexo 20; RMF 2026 2.7.1.32
      (REP a mas tardar el 5o dia natural del mes siguiente al pago).
  R8  Combustible se identifica por concepto: ClaveProdServ familia 1510.
  XAXX  CFDI a RFC generico XAXX010101000 = NO deducible, IVA NO acreditable
        . CFF 29-A-IV, LISR 27-III, LIVA 5-II (regla dura del despacho).

Nota D22: el CFDI declara, solo el banco confirma. Este PT es proyeccion
estimada; la columna manual "Conciliado banco" (hoja detalle) es la respuesta
practica y la agrega el exporter, no esta capa.

Nota 2026-07-25 (feedback real, distincion clave): XAXX en una factura
EMITIDA por el sujeto es un ingreso (facilidad de "factura global" para
publico en general, PT-Emitidas etapa 2) - NUNCA se confunde con esto. Un
XAXX en una factura RECIBIDA (el sujeto es el que gasta) es harina de otro
costal: si viene del SAT, el propio SAT ya filtro por el RFC del sujeto y
un XAXX-receptor simplemente no aparece. Pero si el lote entra por
"Abrir XMLs sueltos..." con XML que llegaron por otra via (el proveedor se
lo mando directo, autofacturacion tipo CFE, o un contador que bajo TODO su
correo sin el filtro que aplica el SAT), SI puede aparecer un gasto
facturado por error a XAXX en vez de al RFC del sujeto - y ese gasto no
debe desaparecer en silencio del PT, debe verse marcado en rojo. Ver
separar_recibidas() para el rescate y su candado (emisor != sujeto) que
evita confundirlo con una global propia.
"""
from datetime import datetime

# --- Catalogos y umbrales (con fundamento) ---------------------------------

RFC_GENERICO = "XAXX010101000"          # publico en general (CFF 29-A-IV)
RFC_GENERICO_EXTRANJERO = "XEXX010101000"  # residente en el extranjero

# c_FormaPago consideradas bancarizadas (R6). 06 "Dinero electronico" entra
# por catalogo aunque LISR 27-III no lo nombre textual (nota de borde (a) del
# ROADMAP §17.2) - se documenta en la hoja Fundamentos.
FORMAS_BANCARIZADAS = frozenset({"02", "03", "04", "05", "06", "28", "29"})
FORMA_POR_DEFINIR = "99"                # legitimo en PPD, anomalia en PUE
FORMA_EFECTIVO = "01"

# Umbral de bancarizacion obligatoria (R1). Se compara contra el MONTO TOTAL
# pagado con IVA incluido (decision del dueno 2026-07-25, ROADMAP §17.7 p.4).
UMBRAL_BANCARIZACION = 2000.0

# Combustible por ClaveProdServ: familia 1510 (R8). Un concepto es combustible
# si su ClaveProdServ (8 digitos) empieza con esta familia (4 digitos).
FAMILIA_COMBUSTIBLE = "1510"

# --- Estatus de deducibilidad (para el semaforo del detalle) ---------------
# El color lo aplica el exporter; aqui solo se nombra el estatus y su nivel.

ESTATUS_DEDUCIBLE = "Deducible"
ESTATUS_NO_DED_GENERICO = "No deducible: receptor genérico (XAXX)"
ESTATUS_NO_DED_COMBUSTIBLE = "No deducible: combustible en efectivo"
ESTATUS_NO_DED_EFECTIVO = "No deducible: efectivo > $2,000"
ESTATUS_PROVISIONADO = "Provisionado: PPD sin REP en el lote"
ESTATUS_INDETERMINADO = "Indeterminado: forma de pago 99"

# Nivel de semaforo por estatus (el exporter traduce a color).
NIVEL_VERDE = "verde"
NIVEL_ROJO = "rojo"
NIVEL_AMBAR = "ambar"

ESTATUS_NIVEL = {
    ESTATUS_DEDUCIBLE: NIVEL_VERDE,
    ESTATUS_NO_DED_GENERICO: NIVEL_ROJO,
    ESTATUS_NO_DED_COMBUSTIBLE: NIVEL_ROJO,
    ESTATUS_NO_DED_EFECTIVO: NIVEL_ROJO,
    ESTATUS_PROVISIONADO: NIVEL_AMBAR,
    ESTATUS_INDETERMINADO: NIVEL_AMBAR,
}


# --- Helpers de extraccion (los parsers formatean "codigo - etiqueta") ------

def _codigo(valor):
    """De 'PUE - Pago en una...' o '01 - Efectivo' devuelve el codigo suelto
    ('PUE', '01'). None/'' -> None."""
    if not valor:
        return None
    return str(valor).split(" - ", 1)[0].strip() or None


def _mes_de(fecha_str):
    """(anio, mes) desde una fecha ya formateada por el parser. Facturas usan
    'DD/MM/YYYY'; los REP usan 'DD/MM/YYYY HH:MM:SS'. None si no se puede."""
    if not fecha_str:
        return None
    texto = str(fecha_str).strip().split(" ", 1)[0]  # descarta la hora si viene
    try:
        dt = datetime.strptime(texto, "%d/%m/%Y")
        return (dt.year, dt.month)
    except ValueError:
        return None


def _num(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _a_mxn(importe, tipo_cambio):
    """Normaliza a MXN (importe x tipo de cambio). El parser ya default-ea el
    tipo de cambio a 1.0 para MXN (ROADMAP §17.3)."""
    return _num(importe) * _num(tipo_cambio, 1.0)


def es_bancarizada(forma_codigo):
    """R6: True si la forma de pago es bancarizada por catalogo."""
    return forma_codigo in FORMAS_BANCARIZADAS


def es_combustible(conceptos_detalle):
    """R8: True si ALGUN concepto es de la familia 1510 (combustible)."""
    for concepto in conceptos_detalle or []:
        clave = str(concepto.get("ClaveProdServ", "")).strip()
        if clave.startswith(FAMILIA_COMBUSTIBLE):
            return True
    return False


# --- Determinacion del sujeto del lote -------------------------------------

def _partes(cfdi):
    """RFCs (emisor y receptor) que intervienen en un CFDI, sin importar el
    tipo (factura/nomina/pago usan claves distintas)."""
    partes = set()
    for clave in ("RFC Emisor", "RFC Emisor CFDI"):
        rfc = cfdi.get(clave)
        if rfc:
            partes.add(rfc)
    for clave in ("RFC Receptor", "RFC Receptor CFDI"):
        rfc = cfdi.get(clave)
        if rfc:
            partes.add(rfc)
    return partes


def determinar_rfc_sujeto(parsed_data_list):
    """RFC que se esta analizando: el que aparece (como emisor o receptor) en
    TODOS los CFDI del lote. Una carga de boveda es SIEMPRE de un solo RFC
    (regla dura D21), asi que ese RFC existe. Si hubiera varios candidatos
    (lote ad-hoc mezclado), gana el que mas veces sea RECEPTOR - el sujeto de
    un analisis de RECIBIDAS es quien recibe. None si el lote esta vacio."""
    if not parsed_data_list:
        return None

    n = len(parsed_data_list)
    aparece_en = {}
    veces_receptor = {}
    for cfdi in parsed_data_list:
        for rfc in _partes(cfdi):
            aparece_en[rfc] = aparece_en.get(rfc, 0) + 1
        receptor = cfdi.get("RFC Receptor") or cfdi.get("RFC Receptor CFDI")
        if receptor:
            veces_receptor[receptor] = veces_receptor.get(receptor, 0) + 1

    presentes_en_todos = [rfc for rfc, veces in aparece_en.items() if veces == n]
    candidatos = presentes_en_todos or list(aparece_en.keys())
    # XAXX/XEXX (publico en general / extranjero) NUNCA es "el sujeto" del
    # analisis - es un RFC generico, no un contribuyente real. Sin este
    # candado, un lote con varios CFDI mal facturados a XAXX (el caso que
    # este mismo cambio empieza a rescatar en separar_recibidas) podria
    # ganarle al sujeto real si aparece como receptor mas veces que el.
    candidatos_validos = [r for r in candidatos
                          if r not in (RFC_GENERICO, RFC_GENERICO_EXTRANJERO)]
    candidatos = candidatos_validos or candidatos  # no dejar la lista vacia

    # Desempate estable: primero por veces-receptor, luego alfabetico.
    return max(candidatos, key=lambda r: (veces_receptor.get(r, 0), r))


# --- Indexado de pagos (REP) por factura PPD -------------------------------

def indexar_pagos_por_uuid(pagos_data):
    """{UUID de factura PPD -> lista de dicts de pago}. Cada REP trae, por
    DoctoRelacionado, el 'IdDocumento Relacionado' = UUID de la factura PPD que
    liquida (R7). Se normaliza a MXN y se guarda el mes del pago (FechaPago) y
    la forma de pago real del REP (FormaDePagoP)."""
    indice = {}
    for pago in pagos_data or []:
        uuid_factura = str(pago.get("IdDocumento Relacionado", "")).strip().upper()
        if not uuid_factura:
            continue
        tc = pago.get("TipoCambioDR", pago.get("TipoCambioP", 1.0))
        registro = {
            "mes": _mes_de(pago.get("FechaPago")),
            "imp_pagado_mxn": _a_mxn(pago.get("ImpPagado"), tc),
            "iva_mxn": _a_mxn(pago.get("IVA 16 Importe"), tc),
            "forma_codigo": _codigo(pago.get("FormaDePagoP")),
            "num_parcialidad": pago.get("NumParcialidad"),
            "imp_saldo_insoluto_mxn": _a_mxn(pago.get("ImpSaldoInsoluto"), tc),
        }
        indice.setdefault(uuid_factura, []).append(registro)
    return indice


# --- Clasificacion por CFDI recibido ---------------------------------------

def _forma_efectiva(metodo, forma_factura, pagos):
    """Forma de pago que REALMENTE aplica (R7): en PUE es la de la factura; en
    PPD es la del REP (la factura PPD no la declara). Devuelve
    (forma_codigo, tiene_rep)."""
    if metodo == "PPD":
        if pagos:
            return pagos[0].get("forma_codigo"), True
        return None, False
    return forma_factura, True  # PUE (o sin metodo): la de la factura


def clasificar_recibida(factura, indice_pagos):
    """Clasifica UNA factura recibida (tipo I). Devuelve un dict con los datos
    base + campos derivados + estatus + nivel de semaforo. No decide color
    (eso es del exporter)."""
    uuid = str(factura.get("UUID", "")).strip().upper()
    receptor = factura.get("RFC Receptor") or ""
    metodo = _codigo(factura.get("Metodo de Pago"))       # PUE / PPD
    forma_factura = _codigo(factura.get("FormaDePago"))    # 01..99
    tc = factura.get("Tipo De Cambio", 1.0)

    total_mxn = _a_mxn(factura.get("Total"), tc)
    iva_mxn = _a_mxn(factura.get("IVA 16%"), tc)
    combustible = es_combustible(factura.get("ConceptosDetalle"))
    pagos = indice_pagos.get(uuid, []) if uuid else []
    forma_efectiva, tiene_rep = _forma_efectiva(metodo, forma_factura, pagos)

    estatus = _estatus(
        receptor=receptor, metodo=metodo, forma_efectiva=forma_efectiva,
        tiene_rep=tiene_rep, total_mxn=total_mxn, combustible=combustible)

    return {
        "uuid": uuid,
        "mes": _mes_de(factura.get("Fecha Emision")),
        "fecha_emision": factura.get("Fecha Emision"),
        "rfc_emisor": factura.get("RFC Emisor"),
        "nombre_emisor": factura.get("Nombre Emisor"),
        "metodo": metodo,
        "forma_factura": forma_factura,
        "forma_efectiva": forma_efectiva,
        "es_combustible": combustible,
        "es_bancarizada": es_bancarizada(forma_efectiva),
        "tiene_rep": tiene_rep,
        "subtotal_mxn": _a_mxn(factura.get("SubTotal"), tc),
        "iva_mxn": iva_mxn,
        "total_mxn": total_mxn,
        "pagos": pagos,
        "estatus": estatus,
        "nivel": ESTATUS_NIVEL[estatus],
    }


def _estatus(receptor, metodo, forma_efectiva, tiene_rep, total_mxn, combustible):
    """Maquina de decision, en orden de prioridad (mas duro/especifico gana).
    Cada rama cita su regla."""
    # XAXX: receptor generico -> no deducible pase lo que pase (CFF 29-A-IV).
    if receptor in (RFC_GENERICO, RFC_GENERICO_EXTRANJERO):
        return ESTATUS_NO_DED_GENERICO

    # PPD sin REP en el lote: aun no es deducible/acreditable (R7). Ambar - no
    # es un error, es que falta el REP; jamas desaparece en silencio.
    if metodo == "PPD" and not tiene_rep:
        return ESTATUS_PROVISIONADO

    # Combustible pagado en efectivo: no deducible sin umbral (R2/R8).
    if combustible and forma_efectiva == FORMA_EFECTIVO:
        return ESTATUS_NO_DED_COMBUSTIBLE

    # Efectivo por arriba del umbral: no deducible (R1).
    if forma_efectiva == FORMA_EFECTIVO and total_mxn > UMBRAL_BANCARIZACION:
        return ESTATUS_NO_DED_EFECTIVO

    # Forma 99 en un pago que ya deberia tenerla definida: indeterminado.
    if forma_efectiva == FORMA_POR_DEFINIR:
        return ESTATUS_INDETERMINADO

    return ESTATUS_DEDUCIBLE


# --- Separacion del lote: facturas recibidas vs notas de credito ------------

# TipoRelacion que netea una NC contra la operacion original (D33): 01
# "Nota de credito de los documentos relacionados", 03 "Devolucion de
# mercancia...". El 07 (anticipos) se lista aparte, fuera del neteo.
TIPOS_RELACION_NETEO = frozenset({"01", "03"})


def _es_recibida(cfdi, rfc_sujeto):
    """True si el sujeto RECIBIO este CFDI (es un gasto suyo). Dos casos:

    1. El sujeto es el RECEPTOR directo (caso normal).
    2. El receptor es generico (XAXX/XEXX) pero el EMISOR no es el sujeto:
       un proveedor le facturo a "publico en general" por error y el sujeto
       de todos modos trae ese CFDI en su carpeta (se lo mando el proveedor,
       autofacturacion tipo CFE, o un contador que bajo TODO su correo sin
       el filtro que aplica el SAT al descargar). Estos NO deben desaparecer
       en silencio del PT: se rescatan aqui para que el clasificador los
       marque en rojo "no deducible: receptor generico" (2026-07-25,
       feedback real del dueño).

    El candado 'emisor != rfc_sujeto' evita que las PROPIAS facturas
    globales EMITIDAS por el sujeto (el se factura a XAXX a si mismo como
    emisor) se cuelen aqui como si fueran un gasto - esas son ingreso, van
    en PT-Emitidas (etapa 2), nunca en Recibidas."""
    if not rfc_sujeto:
        return False
    receptor = cfdi.get("RFC Receptor") or cfdi.get("RFC Receptor CFDI")
    if receptor == rfc_sujeto:
        return True
    emisor = cfdi.get("RFC Emisor") or cfdi.get("RFC Emisor CFDI")
    return receptor in (RFC_GENERICO, RFC_GENERICO_EXTRANJERO) and emisor != rfc_sujeto


def separar_recibidas(parsed_data_list, rfc_sujeto):
    """Parte el lote en (facturas_recibidas tipo I, notas_credito tipo E que
    netean). Solo CFDI donde el sujeto es receptor. Las NC con TipoRelacion
    fuera de 01/03 (p. ej. 07 anticipos) NO entran al neteo - se ignoran aqui
    y podrian listarse aparte en una etapa futura."""
    facturas, notas_credito = [], []
    for cfdi in parsed_data_list or []:
        if cfdi.get("CFDI_Type") != "Invoice" or not _es_recibida(cfdi, rfc_sujeto):
            continue
        tipo = cfdi.get("Tipo")
        if tipo == "NotaCredito":
            tipo_rel = str(cfdi.get("Tipo Relacion") or "").strip()
            uuid_rel = str(cfdi.get("UUID Relacion") or "").strip()
            if tipo_rel in TIPOS_RELACION_NETEO and uuid_rel:
                notas_credito.append(cfdi)
        else:  # "Factura" (tipo I) u otro ingreso ordinario
            facturas.append(cfdi)
    return facturas, notas_credito


# --- Constructores del papel de trabajo ------------------------------------

def construir_detalle(parsed_data_list, rfc_sujeto=None, pagos_data=None):
    """Una fila clasificada por CADA factura recibida (tipo I). El rfc_sujeto y
    los pagos se infieren del lote si no se pasan (comodo para pruebas)."""
    if rfc_sujeto is None:
        rfc_sujeto = determinar_rfc_sujeto(parsed_data_list)
    if pagos_data is None:
        pagos_data = [d for d in (parsed_data_list or [])
                      if d.get("CFDI_Type") == "Pago"]
    indice = indexar_pagos_por_uuid(pagos_data)
    facturas, _ = separar_recibidas(parsed_data_list, rfc_sujeto)
    return [clasificar_recibida(f, indice) for f in facturas]


def _mes_clave(anio_mes):
    return f"{anio_mes[0]:04d}-{anio_mes[1]:02d}" if anio_mes else "Sin fecha"


def _fila_resumen_vacia(mes_clave):
    return {
        "mes": mes_clave,
        "pue_bancarizado": 0.0,
        "pue_efectivo_deducible": 0.0,
        "pue_efectivo_no_deducible": 0.0,
        "combustible_no_deducible": 0.0,
        "ppd_facturado": 0.0,
        "ppd_pagado": 0.0,
        "ppd_provisionado": 0.0,
        "nc_recibidas": 0.0,
        "subtotal_neto": 0.0,
        "iva_neto": 0.0,
        "total_neto": 0.0,
        "iva_acreditable_estimado": 0.0,
    }


def construir_resumen_mensual(parsed_data_list, rfc_sujeto=None, pagos_data=None):
    """Una fila por mes/año (ROADMAP §17.4.1). Anclas temporales (D31):
    - PUE y PPD facturado -> mes de EMISION.
    - PPD pagado y su IVA acreditable -> mes de FechaPago del REP (flujo).
    - NC -> mes del evento (emision de la NC).
    Devuelve la lista ordenada por mes."""
    if rfc_sujeto is None:
        rfc_sujeto = determinar_rfc_sujeto(parsed_data_list)
    if pagos_data is None:
        pagos_data = [d for d in (parsed_data_list or [])
                      if d.get("CFDI_Type") == "Pago"]

    detalle = construir_detalle(parsed_data_list, rfc_sujeto, pagos_data)
    _, notas_credito = separar_recibidas(parsed_data_list, rfc_sujeto)

    filas = {}

    def fila(mes_clave):
        return filas.setdefault(mes_clave, _fila_resumen_vacia(mes_clave))

    for reg in detalle:
        mes_emision = _mes_clave(reg["mes"])
        f = fila(mes_emision)
        f["subtotal_neto"] += reg["subtotal_mxn"]
        f["total_neto"] += reg["total_mxn"]

        if reg["metodo"] == "PPD":
            f["ppd_facturado"] += reg["total_mxn"]
            pagado = sum(p["imp_pagado_mxn"] for p in reg["pagos"])
            f["ppd_provisionado"] += max(reg["total_mxn"] - pagado, 0.0)
            # Cada REP suma a SU mes (flujo), no al de emision.
            for p in reg["pagos"]:
                fp = fila(_mes_clave(p["mes"]))
                fp["ppd_pagado"] += p["imp_pagado_mxn"]
                fp["iva_acreditable_estimado"] += p["iva_mxn"]
        else:  # PUE (o sin metodo)
            f["iva_neto"] += reg["iva_mxn"]
            if reg["es_combustible"] and reg["forma_efectiva"] == FORMA_EFECTIVO:
                f["combustible_no_deducible"] += reg["total_mxn"]
            elif reg["es_bancarizada"]:
                f["pue_bancarizado"] += reg["total_mxn"]
            elif reg["forma_efectiva"] == FORMA_EFECTIVO:
                if reg["total_mxn"] > UMBRAL_BANCARIZACION:
                    f["pue_efectivo_no_deducible"] += reg["total_mxn"]
                else:
                    f["pue_efectivo_deducible"] += reg["total_mxn"]
            # IVA acreditable estimado del mes: solo de PUE deducibles (R3).
            if reg["estatus"] == ESTATUS_DEDUCIBLE:
                f["iva_acreditable_estimado"] += reg["iva_mxn"]

    # Notas de credito: netean en el mes del evento (D33/R5).
    for nc in notas_credito:
        tc = nc.get("Tipo De Cambio", 1.0)
        f = fila(_mes_clave(_mes_de(nc.get("Fecha Emision"))))
        total_nc = _a_mxn(nc.get("Total"), tc)
        iva_nc = _a_mxn(nc.get("IVA 16%"), tc)
        f["nc_recibidas"] += total_nc
        f["total_neto"] -= total_nc
        f["subtotal_neto"] -= _a_mxn(nc.get("SubTotal"), tc)
        f["iva_neto"] -= iva_nc
        f["iva_acreditable_estimado"] -= iva_nc  # restitucion del IVA (R5)

    return [filas[clave] for clave in sorted(filas)]
