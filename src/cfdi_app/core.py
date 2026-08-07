# --- cfdi_app/core.py ---
# Pipeline de procesamiento CFDI SIN interfaz de usuario.
#
# Este modulo es la "fuente unica de verdad" del flujo carpeta -> parseo -> Excel.
# Tanto el CLI (cli.py) como la GUI (ui/main_window.py) lo importan, para que
# exista UNA sola implementacion del procesamiento. Aqui NO hay Tkinter, PySide6,
# print() de UI ni input(): solo logica pura + callbacks opcionales para reportar
# avance. Esto respeta la regla de aislamiento por version de PROMPT.md/ROADMAP.md:
# el despacho vive aqui, pero cada version sigue teniendo su propio modulo parser.
import logging
import os
import platform
import re
import unicodedata
import subprocess
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime

# Parsers aislados por version (NO se fusionan; ver PROMPT.md/ROADMAP.md Sec.2).
from cfdi_app.parsers.xml_parser_33 import parse_cfdi_33_invoice
from cfdi_app.parsers.xml_parser_40 import parse_cfdi_40_invoice
from cfdi_app.parsers.pagos_parser_20 import parse_cfdi_pago_20
from cfdi_app.exporters.excel_exporter import export_to_excel
from cfdi_app.exporters.csv_exporter import export_rows_to_csv
from cfdi_app.constants import (
    INVOICE_COLUMN_ORDER, PAGOS_COLUMN_ORDER, INTERNAL_ONLY_FIELDS,
)
from cfdi_app import paths, settings

logger = logging.getLogger(__name__)

# Re-exportar rutas para no romper a quien ya las importaba desde core.
BASE_APP_DIR = paths.BASE_APP_DIR
BOVEDA_XML_DIR = paths.BOVEDA_XML_DIR
REPORTS_DIR = paths.REPORTS_DIR
create_initial_directories = paths.create_initial_directories
read_last_used_directory = paths.read_last_used_directory
save_last_used_directory = paths.save_last_used_directory


# --- Despacho por version (logica de deteccion) ----------------------------
def parse_xml_file_by_version(xml_file_path):
    """
    Lee el XML para determinar su version CFDI y llama al parser apropiado.
    Detecta tambien si es un CFDI de Pagos 2.0.

    Devuelve una tupla (data, error_message):
        - data: dict (Invoice/Nomina), lista de dicts (Pagos), o None.
        - error_message: None si tuvo exito; una razon legible si no.

    ROADMAP.md Sec.6.5: antes esta funcion devolvia solo None en cualquier
    fallo, sin registrar la causa. Ahora el llamador (process_path) puede
    reportar, por archivo, POR QUE fallo.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        cfdi_version = root.get("Version")
        tipo_comprobante = root.get("TipoDeComprobante")

        # Priorizar deteccion de Pagos 2.0
        if tipo_comprobante == "P" and cfdi_version == "4.0":
            return parse_cfdi_pago_20(xml_file_path), None
        elif cfdi_version == "3.3":
            return parse_cfdi_33_invoice(xml_file_path), None
        elif cfdi_version == "4.0":
            return parse_cfdi_40_invoice(xml_file_path), None
        else:
            return None, (
                f"Version/TipoDeComprobante no soportado "
                f"(Version='{cfdi_version}', TipoDeComprobante='{tipo_comprobante}')")
    except ET.ParseError as e:
        return None, f"XML malformado: {e}"
    except Exception as e:
        logger.exception("Error inesperado al parsear %s", xml_file_path)
        return None, f"Error inesperado: {e}"


def process_zip_file(zip_path, on_log=None):
    """Extrae los XMLs de un .zip a una carpeta temporal y los procesa.

    Devuelve (extracted_data, errors) donde errors es una lista de tuplas
    (etiqueta, razon). Un .zip corrupto ya NO propaga la excepcion sin
    control (antes tumbaba todo process_path); se reporta como error del zip.
    """
    def log(msg):
        if on_log:
            on_log(msg)

    extracted_data = []
    errors = []
    zip_name = os.path.basename(zip_path)

    try:
        temp_dir = tempfile.mkdtemp()
    except OSError as e:
        return extracted_data, [(zip_name, f"No se pudo crear carpeta temporal: {e}")]

    try:
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
        except (zipfile.BadZipFile, OSError) as e:
            errors.append((zip_name, f"Archivo ZIP invalido o dañado: {e}"))
            return extracted_data, errors

        for root_dir, _, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(".xml"):
                    xml_path = os.path.join(root_dir, file)
                    label = f"{zip_name}::{file}"
                    log(f" - Procesando {label}...")
                    data, error = parse_xml_file_by_version(xml_path)
                    if error:
                        errors.append((label, error))
                    elif data:
                        if isinstance(data, list):
                            extracted_data.extend(data)
                        else:
                            extracted_data.append(data)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)  # Limpiar archivos temporales

    return extracted_data, errors


# --- Resultado del procesamiento -------------------------------------------
class ProcessResult:
    """Contenedor simple con los datos parseados, contadores y errores."""

    def __init__(self):
        self.all_parsed_data = []
        self.invoice_data = []
        self.nomina_data = []
        self.pagos_data = []
        self.processed_count = 0
        self.error_count = 0
        self.errors = []  # lista de tuplas (archivo_o_etiqueta, razon)

    @property
    def has_data(self):
        return bool(self.all_parsed_data)


def _collect_target_files(input_folder):
    """Lista los archivos .xml/.zip bajo input_folder (para conocer el total)."""
    targets = []
    for root_dir, _, files in os.walk(input_folder):
        for file in files:
            lower = file.lower()
            if lower.endswith(".xml") or lower.endswith(".zip"):
                targets.append(os.path.join(root_dir, file))
    return targets


def _process_target_files(targets, result, on_log=None, on_progress=None):
    """Parsea una lista YA resuelta de archivos .xml/.zip sobre `result`.

    Nucleo compartido por `process_path` (una carpeta) y `process_paths`
    (varias carpetas de la boveda). La logica de parseo por archivo es
    IDENTICA en ambos flujos: la barra lateral B3 es solo un constructor de
    lista de archivos delante del mismo motor, no un motor nuevo.
    """
    def log(msg):
        if on_log:
            on_log(msg)

    total = len(targets)
    for index, path in enumerate(targets, start=1):
        file = os.path.basename(path)
        if on_progress:
            on_progress(index, total, file)

        lower = file.lower()
        if lower.endswith(".xml"):
            log(f" - Procesando {file}...")
            parsed_data, error = parse_xml_file_by_version(path)
            if error:
                result.error_count += 1
                result.errors.append((path, error))
                log(f"   ERROR: {error}")
            elif parsed_data:
                if isinstance(parsed_data, list):
                    result.all_parsed_data.extend(parsed_data)
                    result.processed_count += len(parsed_data)
                else:
                    result.all_parsed_data.append(parsed_data)
                    result.processed_count += 1
        elif lower.endswith(".zip"):
            log(f" - Descomprimiendo y procesando {file}...")
            zip_results, zip_errors = process_zip_file(path, on_log=on_log)
            if zip_results:
                result.all_parsed_data.extend(zip_results)
                result.processed_count += len(zip_results)
            if zip_errors:
                result.error_count += len(zip_errors)
                result.errors.extend(zip_errors)
                for label, reason in zip_errors:
                    log(f"   ERROR ({label}): {reason}")


def _classify_buckets(result):
    """Separa los registros parseados por tipo para las hojas del Excel."""
    result.invoice_data = [
        d for d in result.all_parsed_data if d.get("CFDI_Type") == "Invoice"]
    result.nomina_data = [
        d for d in result.all_parsed_data if d.get("CFDI_Type") == "Nomina"]
    result.pagos_data = [
        d for d in result.all_parsed_data if d.get("CFDI_Type") == "Pago"]


def process_path(input_folder, on_log=None, on_progress=None):
    """
    Recorre input_folder, parsea cada XML/ZIP y devuelve un ProcessResult.

    Callbacks opcionales (para CLI o GUI; pueden ser None):
        on_log(mensaje:str)               -> mensaje de progreso legible
        on_progress(actual:int, total:int, nombre:str) -> avance numerico

    Es agnostico de la UI: no imprime ni abre ventanas.
    """
    def log(msg):
        if on_log:
            on_log(msg)

    result = ProcessResult()

    if not input_folder or not os.path.isdir(input_folder):
        log(f"Ruta invalida: {input_folder}")
        result.errors.append((str(input_folder), "Ruta invalida o no es un directorio"))
        return result

    targets = _collect_target_files(input_folder)
    total = len(targets)
    log(f"Escaneando directorio: {input_folder} ({total} archivo(s) encontrados)")

    _process_target_files(targets, result, on_log=on_log, on_progress=on_progress)
    _classify_buckets(result)
    return result


def process_paths(folders, on_log=None, on_progress=None):
    """
    Igual que `process_path` pero sobre VARIAS carpetas (flujo de la boveda B3).

    Reune los archivos .xml/.zip de todas las carpetas, DEDUPLICA a nivel de
    archivo (una seleccion de "año completo" mas meses sueltos del mismo año
    resolveria a rutas solapadas) y los procesa con el MISMO motor que
    `process_path`. La barra progreso avanza sobre el total combinado.

    Carpetas invalidas se reportan como error pero no detienen al resto.
    """
    def log(msg):
        if on_log:
            on_log(msg)

    result = ProcessResult()
    folders = list(folders or [])

    targets = []
    seen = set()
    for folder in folders:
        if not folder or not os.path.isdir(folder):
            log(f"Ruta invalida: {folder}")
            result.errors.append((str(folder), "Ruta invalida o no es un directorio"))
            continue
        for path in _collect_target_files(folder):
            key = os.path.normcase(os.path.abspath(path))
            if key not in seen:
                seen.add(key)
                targets.append(path)

    log(f"Escaneando {len(folders)} carpeta(s): "
        f"{len(targets)} archivo(s) encontrados")

    _process_target_files(targets, result, on_log=on_log, on_progress=on_progress)
    _classify_buckets(result)
    return result


# --- Nombre de archivo dinamico --------------------------------------------
def determine_file_naming_components(parsed_data_list):
    """
    Determina RFC, TypeOfXML (Emitidas/Recibidas/Mixed) y Year_Month para el
    nombre del archivo. (Logica original conservada sin cambios de comportamiento.)
    """
    if not parsed_data_list:
        return "Generic", "Report", "UnknownDate"

    all_rfcs_emisor = set()
    all_rfcs_receptor = set()
    all_dates_set = set()  # tuplas (anio, mes)

    def parse_date_string(date_str_val):
        if not date_str_val:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str_val, fmt)
            except ValueError:
                continue
        return None

    for data in parsed_data_list:
        emisor_rfc = data.get("RFC Emisor") or data.get("RFC Emisor CFDI")
        receptor_rfc = data.get("RFC Receptor") or data.get("RFC Receptor CFDI")

        if emisor_rfc:
            all_rfcs_emisor.add(emisor_rfc)
        if receptor_rfc:
            all_rfcs_receptor.add(receptor_rfc)

        date_str = data.get("Fecha Emision")
        if not date_str:
            date_str = data.get("Fecha Timbrado")
        if not date_str and data.get("CFDI_Type") == "Pago":
            date_str = data.get("FechaPago")

        dt_object = parse_date_string(date_str)
        if dt_object:
            all_dates_set.add((dt_object.year, dt_object.month))

    rfc_part = "MixedRFCs"
    type_of_xml_part = "Report"

    # Priorizar el caso de Nomina unica.
    is_all_nomina = all(d.get("CFDI_Type") ==
                        "Nomina" for d in parsed_data_list)
    if is_all_nomina and len(all_rfcs_receptor) == 1:
        rfc_part = list(all_rfcs_receptor)[0]
        type_of_xml_part = "Recibidas"
    else:
        if len(all_rfcs_emisor) == 1:
            dominant_rfc = list(all_rfcs_emisor)[0]
            if len(all_rfcs_receptor) == 1 and list(all_rfcs_receptor)[0] == dominant_rfc:
                rfc_part = dominant_rfc
                type_of_xml_part = "Mixed"
            else:
                rfc_part = dominant_rfc
                type_of_xml_part = "Emitidas"
        elif len(all_rfcs_receptor) == 1:
            dominant_rfc = list(all_rfcs_receptor)[0]
            rfc_part = dominant_rfc
            type_of_xml_part = "Recibidas"
        else:
            unique_combined_rfcs = all_rfcs_emisor.union(all_rfcs_receptor)
            if len(unique_combined_rfcs) == 1:
                rfc_part = list(unique_combined_rfcs)[0]
                type_of_xml_part = "Mixed"

    year_month_part = "UnknownDate"
    if len(all_dates_set) == 1:
        year, month = list(all_dates_set)[0]
        year_month_part = f"{year}_{month:02d}"
    elif len(all_dates_set) > 1:
        sorted_dates = sorted(list(all_dates_set))
        min_year, min_month = sorted_dates[0]
        max_year, max_month = sorted_dates[-1]
        if min_year != max_year:
            year_month_part = f"MixedDates_{min_year}-{max_year}"
        else:
            year_month_part = f"{min_year}_{min_month:02d}-{max_month:02d}"

    return rfc_part, type_of_xml_part, year_month_part


def build_default_filename(parsed_data_list):
    """Construye el nombre sugerido del Excel a partir de los datos parseados."""
    rfc_part, type_part, date_part = determine_file_naming_components(
        parsed_data_list)
    return f"{rfc_part}_{type_part}_{date_part}.xlsx"


def export_report(result, output_path):
    """Exporta el ProcessResult a un archivo Excel multi-hoja.

    Puede propagar excepciones (p. ej. PermissionError si el archivo destino
    esta abierto en Excel) - ver ROADMAP.md Sec.6.6. El llamador decide como
    mostrarlas.

    F2.8 (D30/§17.6): el gate de Papel de Trabajo se lee AQUI (settings), no en
    el exporter - asi el exporter sigue siendo agnostico y una prueba puede
    forzar incluir_pt sin tocar settings.
    """
    export_to_excel(result.invoice_data, result.nomina_data,
                    result.pagos_data, output_path,
                    incluir_pt=settings.get_papel_trabajo_enabled())


def export_report_filtered(invoice_data, nomina_data, pagos_data, output_path):
    """Igual que export_report, pero recibe listas YA filtradas por el
    llamador (F2.7, ROADMAP.md D29/§16) en vez de un ProcessResult completo -
    cada hoja del Excel sale segun SU PROPIO filtro de pestaña. La funcion de
    export no sabe ni le importa que hubo un filtro: es la MISMA
    export_to_excel de siempre, solo con listas mas cortas.

    NO incluye hojas PT (D34): un papel de trabajo fiscal sobre datos filtrados
    seria un resumen mentiroso; el PT solo sale en la exportacion completa."""
    export_to_excel(invoice_data, nomina_data, pagos_data, output_path,
                    incluir_pt=False)


# Traduccion de operadores ANTES de sanitizar (D29/§16.4): un query como
# "total>=5000" no debe perder el operador al filtrar caracteres no
# alfanumericos - se traduce a palabra primero. Orden IMPORTA: "<=" y ">="
# deben probarse antes que "<" y ">" solos, o el resto ("=") quedaria huerfano.
_FILTER_OPERATOR_WORDS = [
    ("<=", "hasta"),
    (">=", "desde"),
    ("<", "menor"),
    (">", "mayor"),
]
_FILTER_SUFFIX_JUNK_RE = re.compile(r"[^A-Za-z0-9_-]+")
_FILTER_SUFFIX_MAX_LEN = 30


def _sanitize_filter_suffix(query):
    """Convierte un query de busqueda del visor (o, desde F2.9/D45, un
    titulo de pestaña como "Nómina") en un sufijo de archivo seguro
    (D29/§16.4). Devuelve None si no queda nada usable (el llamador cae al
    sufijo generico "_Filtrado").

    Los acentos/eñes se NORMALIZAN a su letra base (NFKD + descartar marcas
    combinantes) ANTES de filtrar caracteres no-ASCII, no se pierden en
    silencio - "Nómina" -> "Nomina", no "Nmina". Bug real encontrado
    2026-07-25 al reusar esta funcion para nombres de pestaña (F2.9): con
    solo queries de busqueda tipeadas por el usuario nunca se habia notado
    que una letra acentuada simplemente desaparecia."""
    text = query.strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    for symbol, word in _FILTER_OPERATOR_WORDS:
        text = text.replace(symbol, word)
    text = text.replace(" ", "_")
    text = _FILTER_SUFFIX_JUNK_RE.sub("", text)
    text = text[:_FILTER_SUFFIX_MAX_LEN]
    return text or None


def build_filtered_filename(parsed_data_list, active_queries):
    """Nombre del Excel filtrado (D29/§16.4): mismo nombre base que el export
    completo (RFC/tipo/fecha NO cambian por filtrar) + sufijo derivado.

    `active_queries` es la lista de queries (str) de las pestañas con filtro
    activo en ESE momento. Con exactamente UNA pestaña filtrada se deriva un
    sufijo legible del query (p. ej. "_Filtrado_tela",
    "_Filtrado_menor2000"); con varias a la vez, o si el query sanitizado
    queda vacio, se usa el sufijo generico "_Filtrado".
    """
    base_name = build_default_filename(parsed_data_list)
    stem, ext = os.path.splitext(base_name)

    suffix = None
    if len(active_queries) == 1:
        suffix = _sanitize_filter_suffix(active_queries[0])

    if suffix:
        return f"{stem}_Filtrado_{suffix}{ext}"
    return f"{stem}_Filtrado{ext}"


# --- F2.9: exportacion CSV de una pestaña del visor (ROADMAP.md D43-D45) ---

def full_columns_for_tab(tab_key, rows):
    """Lista COMPLETA de columnas (opcion "Todas las columnas" de §18.4) para
    la pestaña `tab_key` ("invoice_data"/"nomina_data"/"pagos_data").

    Facturas y Pagos ya tienen un orden fijo oficial (mismas listas que usa
    el Excel completo). Nomina NO tiene una lista fija (deuda tecnica ya
    documentada en excel_exporter.py) - se resuelve por union de las claves
    presentes en `rows`, en orden de PRIMERA aparicion (deterministico,
    reproducible corrida tras corrida), excluyendo los mismos campos
    internos que el Excel ya excluye (CFDI_Type + INTERNAL_ONLY_FIELDS).
    """
    if tab_key == "invoice_data":
        return [c for c in INVOICE_COLUMN_ORDER if c != "CFDI_Type"]
    if tab_key == "pagos_data":
        return [c for c in PAGOS_COLUMN_ORDER if c != "CFDI_Type"]

    excluidos = {"CFDI_Type"} | set(INTERNAL_ONLY_FIELDS)
    vistas = []
    vistas_set = set()
    for row in rows:
        for key in row:
            if key in excluidos or key in vistas_set:
                continue
            vistas.append(key)
            vistas_set.add(key)
    return vistas


def build_csv_filename(parsed_data_list, tab_title, query=""):
    """Nombre del CSV (D45/§18.5): mismo nombre base que el Excel + nombre de
    la pestaña + sufijo de filtro (si `query` no esta vacio), extension
    .csv. Ej.: "XAXX..._Recibidas_2026_06_Facturas_Filtrado_tela.csv".

    Reusa _sanitize_filter_suffix tanto para el titulo de pestaña como para
    el query - mismas reglas de sanitizacion en un solo lugar (D29)."""
    base_name = build_default_filename(parsed_data_list)
    stem, _ext = os.path.splitext(base_name)
    tab_suffix = _sanitize_filter_suffix(tab_title) or "Datos"

    query = (query or "").strip()
    if not query:
        return f"{stem}_{tab_suffix}.csv"

    filtro_suffix = _sanitize_filter_suffix(query)
    if filtro_suffix:
        return f"{stem}_{tab_suffix}_Filtrado_{filtro_suffix}.csv"
    return f"{stem}_{tab_suffix}_Filtrado.csv"


def export_tab_csv(rows, columns, output_path, preamble_lines=None):
    """Exporta UNA tabla del visor a CSV (D43). `rows`/`columns` YA resueltos
    por el llamador - hoy siempre via build_csv_export() (D46-D48), que
    curó valores, agregó campos derivados y separó columnas constantes en
    `preamble_lines`. Puede propagar excepciones igual que export_report
    (Sec.6.6) - el llamador decide como mostrarlas."""
    export_rows_to_csv(rows, columns, output_path, preamble_lines=preamble_lines)


def _dedup_extend(base_columns, extra_columns):
    """`base_columns` + los de `extra_columns` que NO esten ya presentes,
    preservando orden, sin duplicar. Usado para agregar las columnas de
    suficiencia (D48) al modo "Todas las columnas" sin arriesgar una
    columna repetida si el Excel ya la trae."""
    result = list(base_columns)
    seen = set(result)
    for col in extra_columns:
        if col not in seen:
            result.append(col)
            seen.add(col)
    return result


def build_csv_export(tab_key, rows, all_columns, full_batch_invoice_data):
    """Arma (preamble_lines, columnas, filas_curadas) listas para
    export_tab_csv() - F2.9 correcciones tras prueba real (D46-D48).

    `rows`: YA filtradas por el llamador (ResultsView.active_tab_export_data,
    respeta el filtro activo de esa pestaña, §16.5).
    `all_columns`: False -> set curado (D46-D48); True -> las columnas
    completas del Excel + las de suficiencia agregadas (D48) - SIN hoisting,
    "todas las columnas" significa ver TODO, no recortar nada.
    `full_batch_invoice_data`: ProcessResult.invoice_data COMPLETO (sin
    filtrar) - la mejor oportunidad de resolver el cruce con el CFDI
    relacionado (D48/#11), independiente del filtro activo en pantalla.

    Import local de reports.csv_curation a proposito (mismo patron que
    excel_exporter.py con pt_exporter): la exportacion base no debe cargar
    la capa de curacion CSV si no se le pide.
    """
    from cfdi_app.reports import csv_curation as cur

    uuid_index = cur.build_uuid_index(full_batch_invoice_data)

    if tab_key == "invoice_data":
        enriched_rows = [cur.enrich_invoice_row(r, uuid_index) for r in rows]
        columns = (list(cur.CSV_INVOICE_COLUMNS) if not all_columns else
                  _dedup_extend(full_columns_for_tab(tab_key, rows),
                               cur.EXTRA_INVOICE_COLUMNS))
    elif tab_key == "pagos_data":
        enriched_rows = [cur.enrich_pagos_row(r, uuid_index) for r in rows]
        columns = (list(cur.CSV_PAGOS_COLUMNS) if not all_columns else
                  _dedup_extend(full_columns_for_tab(tab_key, rows),
                               cur.EXTRA_PAGOS_COLUMNS))
    else:  # nomina_data - sin campos derivados en esta ronda
        enriched_rows = rows
        columns = (list(cur.CSV_NOMINA_COLUMNS) if not all_columns else
                  full_columns_for_tab(tab_key, rows))

    # Curar PRIMERO (fechas ISO, dinero a 2 decimales, UUID mayusculas,
    # codigo+etiqueta) y RECIEN DESPUES decidir que es constante: la
    # curacion es 1-a-1, asi que si los valores crudos eran identicos entre
    # filas, los curados tambien lo son (y viceversa) - no cambia el
    # resultado del hoisting, solo evita curar dos veces.
    curated_rows = [cur.curate_row(r, columns) for r in enriched_rows]

    if all_columns:
        # "Todas las columnas" = ver TODO; el hoisting es una forma de
        # recorte y solo aplica al set curado por default (D46).
        return [], columns, curated_rows

    constantes, columnas_restantes, filas_finales = cur.hoist_constant_columns(
        curated_rows, columns)
    preamble = cur.build_preamble_lines(constantes)
    return preamble, columnas_restantes, filas_finales


def open_file(path):
    """Abre un archivo con la aplicacion por defecto del sistema operativo."""
    if platform.system() == "Windows":
        os.startfile(path)  # noqa: P204 (API de Windows)
    else:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        subprocess.call([opener, path])


def open_folder(path):
    """Abre el explorador de archivos DIRECTAMENTE en `path` (a diferencia de
    open_containing_folder, que abre el padre de un ARCHIVO y lo selecciona).
    Usada por la pagina de Reportes para abrir REPORTS_DIR completa."""
    if platform.system() == "Windows":
        os.startfile(path)  # noqa: P204 (API de Windows)
    else:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        subprocess.call([opener, path])


def open_containing_folder(path):
    """Abre el explorador de archivos en la carpeta que contiene `path`,
    seleccionando el archivo si el sistema operativo lo permite (Windows)."""
    folder = os.path.dirname(path) or "."
    if platform.system() == "Windows":
        try:
            subprocess.run(["explorer", f"/select,{os.path.normpath(path)}"])
        except OSError:
            os.startfile(folder)  # noqa: P204 (API de Windows)
    else:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        subprocess.call([opener, folder])
