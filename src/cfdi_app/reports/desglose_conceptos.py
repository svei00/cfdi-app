# --- cfdi_app/reports/desglose_conceptos.py ---
"""Desglose de conceptos (F2.10, docs/design-f2.10-desglose-conceptos.md).

Capa PURA (sin Qt ni openpyxl): aplana cada CFDI del lote a "lineas de
desglose" (D50) y arma las agregaciones que alimentan el Excel de
exporters/desglose_exporter.py.

Una factura normal da una linea por Concepto (origen "CFDI"). Un CFDI con el
complemento EstadoDeCuentaCombustible (monederos tipo Edenred, D49) da ademas
una linea por CARGA (origen "ECC"): ahi vive la gasolina real, sus litros y su
IVA - el concepto del comprobante es solo la comision.

Alcance (D53): el lote que recibe (lo cargado desde la boveda). No consulta
SQLite ni recorre carpetas. Mes ancla = fecha de emision del CFDI (D51).

Reglas de aplanado (diseño §3.2):
  - Solo entran Factura (I) y NotaCredito (E). Pago, Nomina y Traslado no
    tienen conceptos de gasto.
  - Todo se normaliza a MXN con "Tipo De Cambio" (igual que el PT, D31).
  - Las notas de credito entran en NEGATIVO (importe, descuento, impuestos,
    total y cantidad) para que las sumas por proveedor salgan netas.
  - Una linea con descuento total (ej. etiqueta TAG) entra con total 0; no se
    filtra.
  - El IVA del CFDI y el IVA del complemento NUNCA se mezclan en silencio
    (D54): cada agregacion los trae por separado y suma ambos de forma visible.
  - Los codigos de TipoCombustible se muestran tal cual; su significado no se
    inventa (el XSD ecc12 aun no esta en docs/, ver diseño §3.1).
"""
import re
from collections import OrderedDict
from datetime import datetime

from cfdi_app.reports.csv_curation import compute_iva_bases
from cfdi_app.reports.pt_recibidas import FAMILIA_COMBUSTIBLE

ORIGEN_CFDI = "CFDI"
ORIGEN_ECC = "ECC"
CATEGORIA_ECC = "Combustible (monedero)"
CATEGORIA_COMBUSTIBLE = "Combustible"
CATEGORIA_IMPUESTOS_LOCALES = "Impuestos locales"
DESCRIPCION_IMPUESTOS_LOCALES = "IMPUESTOS LOCALES (neto, no por concepto)"

TIPOS_CON_CONCEPTOS = ("Factura", "NotaCredito")

# Tolerancia de redondeo del cuadre (diseño §3.2).
TOLERANCIA_CUADRE = 0.05

ESTATUS_OK = "OK"
ESTATUS_NO_CUADRA = "No cuadra"
ESTATUS_SIN_DETALLE = "Sin detalle por concepto"

SIN_FECHA = "Sin fecha"

# Campos monetarios que cambian de signo en una nota de credito.
_CAMPOS_CON_SIGNO = ("cantidad", "importe", "descuento", "iva", "ieps",
                     "retenciones", "total_linea")

# Mapa de la columna de base de IVA a los nombres cortos de las lineas.
_BASES = OrderedDict([
    ("IVA 16 Base", "base_iva_16"),
    ("IVA 8 Base", "base_iva_8"),
    ("IVA Cero Base", "base_iva_0"),
    ("IVA Exenta Base", "base_iva_exenta"),
])
CAMPOS_BASE = list(_BASES.values())


# --- Helpers ---------------------------------------------------------------

def _num(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _fecha_cfdi(texto):
    """'DD/MM/YYYY[ hh:mm:ss]' (formato del parser) -> ('YYYY-MM-DD', anio,
    mes). Sin fecha valida -> ('', None, None)."""
    if not texto:
        return "", None, None
    try:
        dt = datetime.strptime(str(texto).strip().split(" ", 1)[0], "%d/%m/%Y")
    except ValueError:
        return "", None, None
    return dt.strftime("%Y-%m-%d"), dt.year, dt.month


def _mes_clave(anio, mes):
    return f"{anio:04d}-{mes:02d}" if anio else SIN_FECHA


def _suma_traslados(traslados, impuestos):
    return sum(_num(t.get("Importe")) for t in traslados
               if t.get("Impuesto") in impuestos)


def _bases_de(traslados):
    """Bases de IVA por tasa de UNA linea, reusando compute_iva_bases (D48)."""
    bases = compute_iva_bases([{"Impuestos": {"Traslados": traslados}}])
    return {corto: bases.get(largo, 0.0) for largo, corto in _BASES.items()}


def _es_nota_credito(cfdi):
    return cfdi.get("Tipo") == "NotaCredito"


def _linea_base(cfdi, tc):
    """Campos del comprobante comunes a toda linea (diseño §3.2)."""
    fecha_iso, anio, mes = _fecha_cfdi(cfdi.get("Fecha Emision"))
    return {
        "uuid": str(cfdi.get("UUID") or "").upper(),
        "serie": cfdi.get("Serie") or "",
        "folio": cfdi.get("Folio") or "",
        "factura": cfdi.get("Factura") or "",
        "fecha_cfdi": fecha_iso,
        "anio": anio,
        "mes": mes,
        "mes_clave": _mes_clave(anio, mes),
        "rfc_emisor": cfdi.get("RFC Emisor") or "",
        "nombre_emisor": cfdi.get("Nombre Emisor") or "",
        "rfc_receptor": cfdi.get("RFC Receptor") or "",
        "tipo": cfdi.get("Tipo") or "",
        "forma_pago": cfdi.get("FormaDePago") or "",
        "metodo_pago": cfdi.get("Metodo de Pago") or "",
        "moneda": cfdi.get("Moneda") or "MXN",
        "tipo_cambio": tc,
    }


def _linea_vacia():
    """Campos propios de la linea, en cero/vacios (los llena cada origen)."""
    linea = {
        "origen": "", "num_linea": 0, "clave_prod_serv": "", "descripcion": "",
        "cantidad": 0.0, "unidad": "", "valor_unitario": 0.0,
        "importe": 0.0, "descuento": 0.0, "iva": 0.0, "ieps": 0.0,
        "retenciones": 0.0, "total_linea": 0.0, "categoria": "",
        "tarjeta": "", "rfc_estacion": "", "clave_estacion": "",
        "tipo_combustible": "", "folio_operacion": "", "fecha_carga": "",
    }
    linea.update({campo: 0.0 for campo in CAMPOS_BASE})
    return linea


def _aplicar_signo_y_tc(linea, signo, tc):
    factor = signo * tc
    for campo in _CAMPOS_CON_SIGNO:
        # La cantidad no se convierte de moneda: solo cambia de signo.
        linea[campo] = round(linea[campo] * (signo if campo == "cantidad" else factor), 6)
    for campo in CAMPOS_BASE:
        linea[campo] = round(linea[campo] * factor, 6)
    linea["valor_unitario"] = round(linea["valor_unitario"] * tc, 6)


def _lineas_cfdi(cfdi, base, signo, tc):
    lineas = []
    for n, concepto in enumerate(cfdi.get("ConceptosDetalle") or [], start=1):
        impuestos = concepto.get("Impuestos") or {}
        traslados = impuestos.get("Traslados") or []
        retenciones = impuestos.get("Retenciones") or []

        linea = _linea_vacia()
        linea.update(base)
        clave = str(concepto.get("ClaveProdServ") or "").strip()
        importe = _num(concepto.get("Importe"))
        descuento = _num(concepto.get("Descuento"))
        iva = _suma_traslados(traslados, ("002",))
        ieps = _suma_traslados(traslados, ("003",))
        ret = sum(_num(r.get("Importe")) for r in retenciones)
        descripcion = str(concepto.get("Descripcion") or "").strip()
        linea.update({
            "origen": ORIGEN_CFDI, "num_linea": n, "clave_prod_serv": clave,
            "descripcion": descripcion,
            "cantidad": _num(concepto.get("Cantidad")),
            "unidad": concepto.get("Unidad") or concepto.get("ClaveUnidad") or "",
            "valor_unitario": _num(concepto.get("ValorUnitario")),
            "importe": importe, "descuento": descuento, "iva": iva,
            "ieps": ieps, "retenciones": ret,
            "total_linea": importe - descuento + iva + ieps - ret,
            "categoria": (CATEGORIA_COMBUSTIBLE
                          if clave.startswith(FAMILIA_COMBUSTIBLE)
                          else descripcion),
        })
        linea.update(_bases_de(traslados))
        _aplicar_signo_y_tc(linea, signo, tc)
        lineas.append(linea)

    # Impuestos locales (complemento implocal, ej. ISH de hospedaje): suman al
    # Total del CFDI pero no cuelgan de ningun concepto. Linea explicita para
    # que las sumas cuadren con el comprobante en vez de quedar un hueco.
    locales = (_num(cfdi.get("Total LocalTrasladado"))
               - _num(cfdi.get("Total LocalRetenido")))
    if lineas and abs(locales) > 0.0049:
        linea = _linea_vacia()
        linea.update(base)
        linea.update({
            "origen": ORIGEN_CFDI, "num_linea": len(lineas) + 1,
            "descripcion": DESCRIPCION_IMPUESTOS_LOCALES,
            "categoria": CATEGORIA_IMPUESTOS_LOCALES,
            "total_linea": locales,
        })
        _aplicar_signo_y_tc(linea, signo, tc)
        lineas.append(linea)
    return lineas


def _lineas_ecc(cfdi, base, signo, tc):
    ecc = cfdi.get("EstadoCuentaCombustible")
    if not ecc:
        return []
    lineas = []
    for n, carga in enumerate(ecc.get("Conceptos") or [], start=1):
        traslados = carga.get("Traslados") or []
        importe = _num(carga.get("Importe"))
        iva = _suma_traslados(traslados, ("IVA", "002"))

        linea = _linea_vacia()
        linea.update(base)
        linea.update({
            "origen": ORIGEN_ECC, "num_linea": n,
            "descripcion": str(carga.get("NombreCombustible") or "").strip(),
            "cantidad": _num(carga.get("Cantidad")), "unidad": "L",
            "valor_unitario": _num(carga.get("ValorUnitario")),
            "importe": importe, "iva": iva, "total_linea": importe + iva,
            "categoria": CATEGORIA_ECC,
            "tarjeta": carga.get("Identificador") or "",
            "rfc_estacion": carga.get("Rfc") or "",
            "clave_estacion": carga.get("ClaveEstacion") or "",
            "tipo_combustible": carga.get("TipoCombustible") or "",
            "folio_operacion": carga.get("FolioOperacion") or "",
            "fecha_carga": str(carga.get("Fecha") or "")[:10],
        })
        # La base de IVA de una carga es su importe, a la tasa que declara.
        linea.update(_bases_de([
            {"Impuesto": "002", "TipoFactor": "Tasa", "Base": importe,
             "TasaOCuota": t.get("TasaOCuota")}
            for t in traslados if t.get("Impuesto") in ("IVA", "002")]))
        _aplicar_signo_y_tc(linea, signo, tc)
        lineas.append(linea)
    return lineas


def _entra_al_desglose(cfdi):
    return (cfdi.get("CFDI_Type") == "Invoice"
            and cfdi.get("Tipo") in TIPOS_CON_CONCEPTOS)


# --- Aplanado --------------------------------------------------------------

def aplanar_lote(parsed_data_list):
    """Aplana el lote a lineas de desglose (D50), ordenadas por fecha,
    proveedor, factura y origen (CFDI antes que ECC). No hay deduplicacion
    por UUID: el motor asume el lote ya depurado, como el resto de reportes."""
    lineas = []
    for cfdi in parsed_data_list or []:
        if not _entra_al_desglose(cfdi):
            continue
        tc = _num(cfdi.get("Tipo De Cambio"), 1.0) or 1.0
        signo = -1.0 if _es_nota_credito(cfdi) else 1.0
        base = _linea_base(cfdi, tc)
        lineas.extend(_lineas_cfdi(cfdi, base, signo, tc))
        lineas.extend(_lineas_ecc(cfdi, base, signo, tc))
    lineas.sort(key=lambda l: (l["fecha_cfdi"], l["rfc_emisor"], l["factura"],
                               l["uuid"], l["origen"], l["num_linea"]))
    return lineas


def proveedores(lineas):
    """[(rfc_emisor, nombre, n_cfdi)] ordenado por nombre, para el combo."""
    por_rfc = OrderedDict()
    for l in lineas:
        info = por_rfc.setdefault(l["rfc_emisor"], [l["nombre_emisor"], set()])
        info[1].add(l["uuid"])
    filas = [(rfc, nombre, len(uuids)) for rfc, (nombre, uuids) in por_rfc.items()]
    return sorted(filas, key=lambda f: (f[1], f[0]))


def filtrar_por_proveedor(lineas, rfc_emisor):
    """None o '' = todos los proveedores."""
    if not rfc_emisor:
        return list(lineas)
    return [l for l in lineas if l["rfc_emisor"] == rfc_emisor]


def lineas_de_uuid(lineas, uuid):
    """Para el reporte "por XML" (etapa 3)."""
    uuid = str(uuid or "").upper()
    return [l for l in lineas if l["uuid"] == uuid]


# --- Agregaciones ----------------------------------------------------------

def _acumular(lineas, clave_fn, extra_fn=None):
    """Suma las metricas por grupo. extra_fn(linea, grupo) acumula campos
    adicionales. Devuelve {clave: grupo} en orden de aparicion."""
    grupos = OrderedDict()
    for l in lineas:
        clave = clave_fn(l)
        g = grupos.get(clave)
        if g is None:
            g = grupos[clave] = {
                "_uuids": set(), "n_lineas": 0, "cantidad": 0.0,
                "importe": 0.0, "descuento": 0.0, "iva": 0.0, "total": 0.0,
                "importe_ecc": 0.0, "iva_ecc": 0.0, "total_ecc": 0.0,
            }
            g.update({campo: 0.0 for campo in CAMPOS_BASE})
        g["_uuids"].add(l["uuid"])
        g["n_lineas"] += 1
        g["cantidad"] += l["cantidad"]
        g["importe"] += l["importe"]
        g["descuento"] += l["descuento"]
        g["iva"] += l["iva"]
        g["total"] += l["total_linea"]
        for campo in CAMPOS_BASE:
            g[campo] += l[campo]
        if l["origen"] == ORIGEN_ECC:
            g["importe_ecc"] += l["importe"]
            g["iva_ecc"] += l["iva"]
            g["total_ecc"] += l["total_linea"]
        if extra_fn:
            extra_fn(l, g)
    return grupos


_METRICAS = ("cantidad", "importe", "descuento", "iva", "total",
             "importe_ecc", "iva_ecc", "total_ecc") + tuple(CAMPOS_BASE)


def _cerrar(grupo, **claves):
    fila = dict(claves)
    fila["n_cfdi"] = len(grupo["_uuids"])
    fila["n_lineas"] = grupo["n_lineas"]
    for m in _METRICAS:
        fila[m] = round(grupo[m], 2)
    # D54: el IVA del CFDI y el del complemento, siempre separados y visibles.
    fila["iva_cfdi"] = round(grupo["iva"] - grupo["iva_ecc"], 2)
    return fila


def por_proveedor(lineas):
    grupos = _acumular(lineas, lambda l: (l["rfc_emisor"], l["nombre_emisor"]))
    filas = [_cerrar(g, rfc_emisor=k[0], nombre_emisor=k[1])
             for k, g in grupos.items()]
    return sorted(filas, key=lambda f: (f["nombre_emisor"], f["rfc_emisor"]))


def por_mes(lineas):
    grupos = _acumular(
        lineas, lambda l: (l["mes_clave"], l["rfc_emisor"], l["nombre_emisor"]))
    filas = [_cerrar(g, mes=k[0], rfc_emisor=k[1], nombre_emisor=k[2])
             for k, g in grupos.items()]
    return sorted(filas, key=lambda f: (f["mes"], f["nombre_emisor"], f["rfc_emisor"]))


def por_ejercicio(lineas):
    grupos = _acumular(
        lineas, lambda l: (l["anio"] or 0, l["rfc_emisor"], l["nombre_emisor"]))
    filas = [_cerrar(g, ejercicio=(k[0] or SIN_FECHA), rfc_emisor=k[1],
                      nombre_emisor=k[2]) for k, g in grupos.items()]
    return sorted(filas, key=lambda f: (str(f["ejercicio"]), f["nombre_emisor"], f["rfc_emisor"]))


def por_concepto(lineas):
    grupos = _acumular(lineas, lambda l: (
        l["rfc_emisor"], l["nombre_emisor"], l["clave_prod_serv"],
        l["descripcion"]))
    filas = [_cerrar(g, rfc_emisor=k[0], nombre_emisor=k[1],
                      clave_prod_serv=k[2], descripcion=k[3])
             for k, g in grupos.items()]
    return sorted(filas, key=lambda f: (f["nombre_emisor"], -f["importe"], f["descripcion"]))


def por_iva(lineas):
    """Hoja IVA (D54): por mes y proveedor, IVA del CFDI y del complemento en
    columnas separadas + total, y las bases por tasa (mismo criterio D48)."""
    filas = []
    for f in por_mes(lineas):
        filas.append({
            "mes": f["mes"], "rfc_emisor": f["rfc_emisor"],
            "nombre_emisor": f["nombre_emisor"],
            **{campo: f[campo] for campo in CAMPOS_BASE},
            "iva_cfdi": f["iva_cfdi"], "iva_ecc": f["iva_ecc"],
            "iva_total": f["iva"],
        })
    return filas


def combustible(lineas):
    """Hoja Combustible: solo lineas ECC. Devuelve {'por_tipo', 'por_tarjeta',
    'por_estacion'} (listas de dicts). Agrupa por TipoCombustible - el nombre
    depende de la marca ('Magna' y 'BP REGU' son el mismo tipo 1)."""
    ecc = [l for l in lineas if l["origen"] == ORIGEN_ECC]

    def con_precio(fila):
        fila["precio_promedio"] = (round(fila["importe"] / fila["cantidad"], 3)
                                   if fila["cantidad"] else 0.0)
        return fila

    def acumular_nombres(l, g):
        g.setdefault("_nombres", set()).add(l["descripcion"])
        g.setdefault("_tarjetas", set()).add(l["tarjeta"])

    g_tipo = _acumular(ecc, lambda l: (l["mes_clave"], l["tipo_combustible"]),
                       acumular_nombres)
    por_tipo = [con_precio(_cerrar(
        g, mes=k[0], tipo_combustible=k[1],
        nombres=", ".join(sorted(n for n in g["_nombres"] if n)),
        cargas=g["n_lineas"])) for k, g in g_tipo.items()]

    g_tarjeta = _acumular(ecc, lambda l: (l["mes_clave"], l["tarjeta"]))
    por_tarjeta = [con_precio(_cerrar(
        g, mes=k[0], tarjeta=k[1], cargas=g["n_lineas"]))
        for k, g in g_tarjeta.items()]

    g_estacion = _acumular(ecc, lambda l: (l["rfc_estacion"], l["clave_estacion"]))
    por_estacion = [con_precio(_cerrar(
        g, rfc_estacion=k[0], clave_estacion=k[1], cargas=g["n_lineas"]))
        for k, g in g_estacion.items()]

    return {
        "por_tipo": sorted(por_tipo, key=lambda f: (f["mes"], f["tipo_combustible"])),
        "por_tarjeta": sorted(por_tarjeta, key=lambda f: (f["mes"], f["tarjeta"])),
        "por_estacion": sorted(por_estacion, key=lambda f: -f["importe"]),
    }


def hay_ecc(lineas):
    return any(l["origen"] == ORIGEN_ECC for l in lineas)


# --- Cuadre ----------------------------------------------------------------

def cuadre(parsed_data_list):
    """Una fila por CFDI que entra al desglose. Compara, en MXN:
      - Σ de las lineas CFDI contra el Total declarado del comprobante;
      - si trae ECC: Σ importes contra ECC@SubTotal y Σ importes+IVA contra
        ECC@Total (tolerancia ±0.05 por redondeo).
    Un CFDI sin ConceptosDetalle (hoy el parser 3.3) sale como "Sin detalle
    por concepto": no se inventan lineas."""
    filas = []
    for cfdi in parsed_data_list or []:
        if not _entra_al_desglose(cfdi):
            continue
        tc = _num(cfdi.get("Tipo De Cambio"), 1.0) or 1.0
        signo = -1.0 if _es_nota_credito(cfdi) else 1.0
        base = _linea_base(cfdi, tc)
        fila = {
            "uuid": base["uuid"], "factura": base["factura"],
            "rfc_emisor": base["rfc_emisor"],
            "nombre_emisor": base["nombre_emisor"], "mes": base["mes_clave"],
            "version": cfdi.get("Version") or "",
            "suma_lineas": None, "total_declarado": None,
            "ecc_importe": None, "ecc_subtotal_declarado": None,
            "ecc_total": None, "ecc_total_declarado": None,
            "estatus": ESTATUS_OK, "detalle": "",
        }
        if not cfdi.get("ConceptosDetalle"):
            fila["estatus"] = ESTATUS_SIN_DETALLE
            fila["detalle"] = (f"CFDI {fila['version']} sin detalle por "
                               "concepto: no se generaron lineas.")
            filas.append(fila)
            continue

        problemas = []
        lineas_cfdi = _lineas_cfdi(cfdi, base, signo, tc)
        fila["suma_lineas"] = round(sum(l["total_linea"] for l in lineas_cfdi), 2)
        fila["total_declarado"] = round(signo * tc * _num(cfdi.get("Total")), 2)
        if abs(fila["suma_lineas"] - fila["total_declarado"]) > TOLERANCIA_CUADRE:
            problemas.append("Σ de conceptos ≠ Total del CFDI")

        ecc = cfdi.get("EstadoCuentaCombustible")
        if ecc:
            lineas_ecc = _lineas_ecc(cfdi, base, signo, tc)
            fila["ecc_importe"] = round(sum(l["importe"] for l in lineas_ecc), 2)
            fila["ecc_total"] = round(sum(l["total_linea"] for l in lineas_ecc), 2)
            fila["ecc_subtotal_declarado"] = round(signo * tc * _num(ecc.get("SubTotal")), 2)
            fila["ecc_total_declarado"] = round(signo * tc * _num(ecc.get("Total")), 2)
            if abs(fila["ecc_importe"] - fila["ecc_subtotal_declarado"]) > TOLERANCIA_CUADRE:
                problemas.append("Σ de cargas ≠ SubTotal del complemento")
            if abs(fila["ecc_total"] - fila["ecc_total_declarado"]) > TOLERANCIA_CUADRE:
                problemas.append("Σ de cargas + IVA ≠ Total del complemento")

        if problemas:
            fila["estatus"] = ESTATUS_NO_CUADRA
            fila["detalle"] = "; ".join(problemas)
        filas.append(fila)
    return sorted(filas, key=lambda f: (f["mes"], f["rfc_emisor"], f["factura"]))


def cuadre_fallas(filas_cuadre):
    """Solo los CFDI que no cuadran o no tienen detalle (hoja Cuadre)."""
    return [f for f in filas_cuadre if f["estatus"] != ESTATUS_OK]


# --- Nombre de archivo -----------------------------------------------------

def _rfc_receptor_dominante(lineas):
    conteo = {}
    for l in lineas:
        if l["rfc_receptor"]:
            conteo[l["rfc_receptor"]] = conteo.get(l["rfc_receptor"], 0) + 1
    return max(conteo, key=conteo.get) if conteo else "LOTE"


def _sanear(texto):
    """Solo letras, digitos, guion y guion bajo (seguro como nombre de archivo)."""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", str(texto)).strip("-")


def nombre_archivo(lineas, rfc_emisor=None, sufijo=None):
    """Desglose_<RFC>_<AAAA-MM>[_a_<AAAA-MM>][_<RFC emisor>][_<sufijo>].xlsx,
    derivado del lote (mismo criterio que D29/F2.7). El sufijo de proveedor
    solo se agrega si el usuario filtro por uno (una sola cifra no debe parecer
    el reporte completo); `sufijo` identifica un reporte de UN solo XML (la
    factura), ya saneado."""
    meses = sorted({l["mes_clave"] for l in lineas if l["mes_clave"] != SIN_FECHA})
    if not meses:
        periodo = "SinFecha"
    elif meses[0] == meses[-1]:
        periodo = meses[0]
    else:
        periodo = f"{meses[0]}_a_{meses[-1]}"
    partes = ["Desglose", _rfc_receptor_dominante(lineas), periodo]
    if rfc_emisor:
        partes.append(rfc_emisor)
    if sufijo and _sanear(sufijo):
        partes.append(_sanear(sufijo))
    return "_".join(partes) + ".xlsx"


# --- Reporte "por XML" (etapa 3, diseño §3.4) ------------------------------

# (clave de la linea, encabezado, numerica). Las 4 ultimas solo tienen dato en
# lineas ECC (cargas del complemento de combustible).
COLUMNAS_XML = [
    ("origen", "Origen", False),
    ("num_linea", "Línea", True),
    ("clave_prod_serv", "ClaveProdServ", False),
    ("descripcion", "Descripción", False),
    ("cantidad", "Cantidad", True),
    ("unidad", "Unidad", False),
    ("valor_unitario", "Valor unitario", True),
    ("importe", "Importe", True),
    ("descuento", "Descuento", True),
    ("iva", "IVA", True),
    ("total_linea", "Total", True),
    ("fecha_carga", "Fecha carga", False),
    ("tarjeta", "Tarjeta", False),
    ("rfc_estacion", "RFC estación", False),
    ("tipo_combustible", "Tipo comb.", False),
]
_CAMPOS_PRECIO = ("valor_unitario",)


def _fmt_celda(clave, valor):
    if valor is None or valor == "":
        return ""
    if clave == "num_linea":
        return str(int(valor))
    if isinstance(valor, float):
        decimales = 3 if clave in _CAMPOS_PRECIO else 2
        return f"{valor:,.{decimales}f}"
    return str(valor)


def tabla_xml(lineas):
    """(encabezados, filas, numericas): todo ya como TEXTO listo para pintar
    (separador de miles, 2 decimales). Las columnas de combustible solo se
    incluyen si hay cargas ECC, para no mostrar 4 columnas vacias en una
    factura normal."""
    cols = [c for c in COLUMNAS_XML
            if hay_ecc(lineas) or c[0] not in
            ("fecha_carga", "tarjeta", "rfc_estacion", "tipo_combustible")]
    encabezados = [c[1] for c in cols]
    numericas = [c[2] for c in cols]
    filas = [[_fmt_celda(c[0], l.get(c[0])) for c in cols] for l in lineas]
    return encabezados, filas, numericas


def resumen_xml(lineas):
    """Totales de UN comprobante para el pie del dialogo. El IVA del CFDI y el
    del complemento van separados (D54)."""
    cfdi = [l for l in lineas if l["origen"] == ORIGEN_CFDI]
    ecc = [l for l in lineas if l["origen"] == ORIGEN_ECC]
    iva_cfdi = sum(l["iva"] for l in cfdi)
    iva_ecc = sum(l["iva"] for l in ecc)
    return {
        "lineas_cfdi": len(cfdi),
        "cargas": len(ecc),
        "litros": round(sum(l["cantidad"] for l in ecc), 2),
        "importe": round(sum(l["importe"] for l in lineas), 2),
        "importe_cfdi": round(sum(l["importe"] for l in cfdi), 2),
        "importe_ecc": round(sum(l["importe"] for l in ecc), 2),
        "iva_cfdi": round(iva_cfdi, 2),
        "iva_ecc": round(iva_ecc, 2),
        "iva_total": round(iva_cfdi + iva_ecc, 2),
        "total_cfdi": round(sum(l["total_linea"] for l in cfdi), 2),
        "total_ecc": round(sum(l["total_linea"] for l in ecc), 2),
        "total": round(sum(l["total_linea"] for l in lineas), 2),
    }


def texto_pie_xml(resumen):
    """Pie del dialogo en texto plano (una cadena por renglon)."""
    renglones = [
        f"Conceptos del CFDI: {resumen['lineas_cfdi']}   |   "
        f"Importe: ${resumen['importe_cfdi']:,.2f}   |   "
        f"IVA del CFDI: ${resumen['iva_cfdi']:,.2f}   |   "
        f"Total del CFDI: ${resumen['total_cfdi']:,.2f}",
    ]
    if resumen["cargas"]:
        renglones.append(
            f"Cargas del complemento: {resumen['cargas']}   |   "
            f"Litros: {resumen['litros']:,.2f}   |   "
            f"Importe: ${resumen['importe_ecc']:,.2f}   |   "
            f"IVA del complemento: ${resumen['iva_ecc']:,.2f}   |   "
            f"Total del complemento: ${resumen['total_ecc']:,.2f}")
        renglones.append(
            f"IVA total (CFDI + complemento): ${resumen['iva_total']:,.2f}")
    return renglones
