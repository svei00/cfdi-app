# --- cfdi_app/ui/filtering.py ---
# Logica del filtro incremental del visor (ROADMAP.md D15 / Sec.11), separada
# de Qt a proposito (mismo patron que ui/state.py): funciones puras, faciles
# de leer y de probar sin ventana. El QSortFilterProxyModel de la UI solo
# LLAMA a matches_search(); no reimplementa la logica de comparacion aqui.
#
# Una sola caja de busqueda soporta dos modos:
#   1. Texto libre -> subcadena (sin distinguir mayusculas) contra los
#      campos de `text_fields` (p. ej. RFC, Nombre, Factura, UUID, Conceptos).
#   2. Comparacion numerica -> si el texto es (opcionalmente) un nombre de
#      campo seguido de un operador (<, >, <=, >=) y un numero, p. ej.
#      "<2000" o "subtotal<2000". Sin nombre de campo, se usa
#      `default_amount_field` (ver D15: por defecto es "Total").
import re

_AMOUNT_QUERY_RE = re.compile(
    r"^\s*(?:(?P<field>[a-zA-Z_]+)\s*)?(?P<op><=|>=|<|>)\s*(?P<value>-?\d+(?:\.\d+)?)\s*$"
)

_OPS = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
}


def _as_float(value):
    """Convierte a float de forma tolerante; None/no-numerico -> None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def matches_search(record, query, text_fields, amount_fields, default_amount_field):
    """
    Devuelve True si `record` (dict) coincide con `query`.

    Args:
        record: el registro (dict) a evaluar.
        query: texto escrito por el usuario en la caja de busqueda.
        text_fields: lista de claves de `record` donde buscar subcadena.
        amount_fields: dict {alias_en_minusculas: clave_real_en_record} para
            resolver el nombre de campo opcional en la sintaxis de operador
            (p. ej. {"total": "Total", "subtotal": "SubTotal"}).
        default_amount_field: clave real a usar cuando el operador no
            especifica campo (p. ej. "<2000" sin prefijo).

    Cadena vacia (o solo espacios) siempre coincide (sin filtro activo).
    """
    query = (query or "").strip()
    if not query:
        return True

    amount_match = _AMOUNT_QUERY_RE.match(query)
    if amount_match:
        field_alias = amount_match.group("field")
        op_symbol = amount_match.group("op")
        target_value = float(amount_match.group("value"))

        if field_alias:
            field_key = amount_fields.get(field_alias.lower())
            if field_key is None:
                # Alias no reconocido: degradar a busqueda de texto normal
                # con la cadena completa, en vez de fallar o no coincidir con nada.
                return _matches_text(record, query, text_fields)
        else:
            field_key = default_amount_field

        record_value = _as_float(record.get(field_key))
        if record_value is None:
            return False
        return _OPS[op_symbol](record_value, target_value)

    return _matches_text(record, query, text_fields)


def _matches_text(record, query, text_fields):
    needle = query.lower()
    for field in text_fields:
        haystack = record.get(field)
        if haystack and needle in str(haystack).lower():
            return True
    return False


def filter_records(records, query, text_fields, amount_fields, default_amount_field):
    """Devuelve la sublista de `records` que coincide con `query`."""
    return [
        r for r in records
        if matches_search(r, query, text_fields, amount_fields, default_amount_field)
    ]


def compute_totals(records, amount_fields):
    """
    Suma los campos de `amount_fields` (dict alias->clave_real, o lista de
    claves reales) sobre `records`. Valores no numericos/ausentes cuentan
    como 0.0. Devuelve un dict {clave_real: suma}.
    """
    keys = list(amount_fields.values()) if isinstance(amount_fields, dict) else list(amount_fields)
    totals = {key: 0.0 for key in keys}
    for record in records:
        for key in keys:
            value = _as_float(record.get(key))
            if value is not None:
                totals[key] += value
    return totals
