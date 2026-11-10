# --- cfdi_app/sat_status.py ---
# Estatus de CFDI ante el SAT (F7-lite): vigente / cancelado / no encontrado.
#
# Usa el servicio PUBLICO de validacion de comprobantes del SAT (el mismo de
# los codigos QR): SOAP, sin autenticacion, una consulta por UUID. Verificado
# en vivo con los 630 CFDI de octubre 2026: ~20 consultas/s con 6 hilos.
#
# Modulo PURO (sin Qt): la red entra por `transport` (inyectable en pruebas) y
# el cache es un SQLite local. Solo el estatus de HOY: una factura de octubre
# cancelada en noviembre sale "Cancelado" (igual que en el portal del SAT);
# el servicio no devuelve la fecha de cancelacion.
import logging
import os
import re
import sqlite3
import time
from contextlib import contextmanager
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

SERVICE_URL = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
SOAP_ACTION = "http://tempuri.org/IConsultaCFDIService/Consulta"

VIGENTE = "Vigente"
CANCELADO = "Cancelado"
NO_ENCONTRADO = "No Encontrado"
ERROR = "Error"          # no se pudo consultar (red); NUNCA se guarda en cache

# Cuanto tiempo vale un resultado guardado. Cancelado es definitivo.
_VIGENCIA_CACHE = {VIGENTE: timedelta(days=7), NO_ENCONTRADO: timedelta(days=1)}


# --- Consulta ---------------------------------------------------------------

def build_expression(uuid, rfc_emisor, rfc_receptor, total):
    """Cadena de la expresion impresa del QR: ?re=..&rr=..&tt=..&id=..
    El '&' DENTRO de un RFC (existe: 'ER&0412152P0') debe ir como '&amp;'; sin
    eso el servicio corta el RFC y responde 'No Encontrado' (error propio
    corregido en pruebas con datos reales)."""
    def rfc(valor):
        return str(valor or "").strip().replace("&", "&amp;")
    return (f"?re={rfc(rfc_emisor)}&rr={rfc(rfc_receptor)}"
            f"&tt={float(total or 0):017.6f}&id={str(uuid).strip()}")


def build_envelope(expression):
    return ('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:tem="http://tempuri.org/"><soapenv:Header/><soapenv:Body>'
            f'<tem:Consulta><tem:expresionImpresa><![CDATA[{expression}]]>'
            '</tem:expresionImpresa></tem:Consulta></soapenv:Body></soapenv:Envelope>')


def parse_response(xml_text):
    """Extrae del SOAP de respuesta (estado, es_cancelable, estatus_cancelacion).
    Estado desconocido o respuesta ilegible -> ERROR (no se cachea)."""
    def tag(name):
        m = re.search(rf"<(?:\w+:)?{name}>(.*?)</(?:\w+:)?{name}>", xml_text or "", re.S)
        return m.group(1).strip() if m else ""
    estado = tag("Estado")
    if estado not in (VIGENTE, CANCELADO, NO_ENCONTRADO):
        estado = ERROR
    return {"estado": estado,
            "es_cancelable": tag("EsCancelable"),
            "estatus_cancelacion": tag("EstatusCancelacion")}


def http_transport(expression, timeout=30):
    """Transporte real. Devuelve el texto de la respuesta SOAP."""
    request = urllib.request.Request(
        SERVICE_URL, data=build_envelope(expression).encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": SOAP_ACTION})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def query_status(uuid, rfc_emisor, rfc_receptor, total, transport=http_transport, retries=2):
    """Una consulta con reintentos ante fallo de red. Nunca lanza: un fallo
    definitivo devuelve estado ERROR."""
    expression = build_expression(uuid, rfc_emisor, rfc_receptor, total)
    ultimo = ""
    for intento in range(retries + 1):
        try:
            return parse_response(transport(expression))
        except Exception as exc:  # red, timeout, SSL...
            ultimo = str(exc)[:120]
            if intento < retries:
                time.sleep(1.0 * (intento + 1))
    logger.warning("Consulta SAT fallida para %s: %s", uuid, ultimo)
    return {"estado": ERROR, "es_cancelable": "", "estatus_cancelacion": ""}


# --- Cache SQLite -----------------------------------------------------------


class StatusCache:
    """Cache de resultados por UUID. Una conexion por operacion (los hilos de
    consulta no la comparten; la escritura va siempre desde un solo hilo)."""

    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with self._connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS status ("
                        "uuid TEXT PRIMARY KEY, estado TEXT NOT NULL, "
                        "es_cancelable TEXT, estatus_cancelacion TEXT, "
                        "checked_at TEXT NOT NULL)")

    @contextmanager
    def _connect(self):
        """Abre, hace commit al salir bien y SIEMPRE cierra (sqlite3 por si solo
        no cierra el archivo, y en Windows queda bloqueado)."""
        con = sqlite3.connect(self.path)
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def get(self, uuid, now=None):
        """Resultado guardado si sigue vigente segun su estado, si no None."""
        now = now or datetime.now()
        with self._connect() as con:
            row = con.execute(
                "SELECT estado, es_cancelable, estatus_cancelacion, checked_at "
                "FROM status WHERE uuid=?", (uuid.upper(),)).fetchone()
        if not row:
            return None
        estado, cancelable, estcanc, checked = row
        if estado != CANCELADO:
            edad_max = _VIGENCIA_CACHE.get(estado, timedelta(0))
            if now - datetime.fromisoformat(checked) > edad_max:
                return None
        return {"estado": estado, "es_cancelable": cancelable or "",
                "estatus_cancelacion": estcanc or "", "checked_at": checked}

    def put(self, uuid, result, now=None):
        if result["estado"] == ERROR:
            return
        now = now or datetime.now()
        with self._connect() as con:
            con.execute("INSERT OR REPLACE INTO status VALUES (?,?,?,?,?)",
                        (uuid.upper(), result["estado"], result.get("es_cancelable", ""),
                         result.get("estatus_cancelacion", ""), now.isoformat()))


# --- Verificacion de un lote ------------------------------------------------

def _identity(record):
    """(uuid, rfc_emisor, rfc_receptor, total) de una fila de factura/nomina o
    de pago (las filas de REP usan las claves '... CFDI' y total 0)."""
    if record.get("UUID"):
        return (record["UUID"], record.get("RFC Emisor"), record.get("RFC Receptor"),
                record.get("Total"))
    if record.get("UUID CFDI"):
        return (record["UUID CFDI"], record.get("RFC Emisor CFDI"),
                record.get("RFC Receptor CFDI"), 0.0)
    return None


def collect_targets(records):
    """{UUID en MAYUSCULAS -> (uuid, emisor, receptor, total)}, sin repetir:
    un REP con 30 documentos es UNA consulta."""
    targets = {}
    for record in records:
        ident = _identity(record)
        if ident and ident[0]:
            targets.setdefault(str(ident[0]).strip().upper(), ident)
    return targets


def verify_records(records, cache, transport=http_transport, on_progress=None,
                   max_workers=6, force=False):
    """Consulta (o toma del cache) el estatus de cada UUID distinto de
    `records`, escribe el resultado en record["Estado SAT"] y devuelve el
    resumen {"vigente": n, "cancelado": n, "no_encontrado": n, "error": n,
    "consultados": n, "de_cache": n, "problemas": [(uuid, estado), ...]}.

    `force=True` ignora el cache (re-verificar todo)."""
    records = list(records)
    targets = collect_targets(records)
    resultados = {}
    pendientes = []
    for key, ident in targets.items():
        guardado = None if force else cache.get(key)
        if guardado:
            resultados[key] = guardado
        else:
            pendientes.append((key, ident))
    de_cache = len(resultados)

    total = len(targets)
    hechos = de_cache
    if on_progress:
        on_progress(hechos, total)

    def consultar(item):
        key, (uuid, emisor, receptor, monto) = item
        return key, query_status(uuid, emisor, receptor, monto, transport=transport)

    if pendientes:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for key, resultado in pool.map(consultar, pendientes):
                resultados[key] = resultado
                cache.put(key, resultado)      # un solo hilo escribe
                hechos += 1
                if on_progress:
                    on_progress(hechos, total)

    for record in records:
        ident = _identity(record)
        if ident and ident[0]:
            record["Estado SAT"] = resultados[str(ident[0]).strip().upper()]["estado"]

    resumen = {"vigente": 0, "cancelado": 0, "no_encontrado": 0, "error": 0,
               "consultados": len(pendientes), "de_cache": de_cache, "problemas": []}
    nombres = {VIGENTE: "vigente", CANCELADO: "cancelado",
               NO_ENCONTRADO: "no_encontrado", ERROR: "error"}
    for key, resultado in resultados.items():
        resumen[nombres[resultado["estado"]]] += 1
        if resultado["estado"] != VIGENTE:
            resumen["problemas"].append((key, resultado["estado"]))
    return resumen
