# --- core.py ---
# Pipeline de procesamiento CFDI SIN interfaz de usuario.
#
# Este modulo es la "fuente unica de verdad" del flujo carpeta -> parseo -> Excel.
# Tanto la version de consola (main.py) como la GUI (gui.py) lo importan, para que
# exista UNA sola implementacion del procesamiento. Aqui NO hay Tkinter, PySide6,
# print() de UI ni input(): solo logica pura + callbacks opcionales para reportar
# avance. Esto respeta la regla de aislamiento por version de PROMPT.md: el
# despacho vive aqui, pero cada version sigue teniendo su propio modulo parser.
import os
import platform
import subprocess
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime

# Parsers aislados por version (NO se fusionan; ver PROMPT.md).
from xml_parser_33 import parse_cfdi_33_invoice
from xml_parser_40 import parse_cfdi_40_invoice
from pagos_parser_20 import parse_cfdi_pago_20
from excel_exporter import export_to_excel

# --- Directorios base de la aplicacion -------------------------------------
# Relativo a una carpeta conceptual "AdminXML" dos niveles por encima del script.
# (Pendiente: hacerlo configurable cuando exista el directorio de trabajo del
#  usuario; ver "Planned: working directory & auto-organization" en PROMPT.md.)
BASE_APP_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "AdminXML"))
BOVEDA_XML_DIR = os.path.join(BASE_APP_DIR, "BovedaCFDI")
REPORTS_DIR = os.path.join(BASE_APP_DIR, "Reports")
LAST_USED_DIR_FILE = os.path.join(REPORTS_DIR, "last_used_directory.txt")


def create_initial_directories():
    """Crea los directorios base de la aplicacion si no existen."""
    os.makedirs(BASE_APP_DIR, exist_ok=True)
    os.makedirs(BOVEDA_XML_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)


def read_last_used_directory():
    """Devuelve el ultimo directorio usado (si sigue siendo valido) o ''. """
    if os.path.exists(LAST_USED_DIR_FILE):
        try:
            with open(LAST_USED_DIR_FILE, "r") as f:
                last_dir = f.read().strip()
            if os.path.isdir(last_dir):
                return last_dir
        except Exception:
            pass
    return ""


def save_last_used_directory(directory):
    """Guarda el directorio seleccionado para recordarlo en la proxima sesion."""
    if not directory:
        return
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(LAST_USED_DIR_FILE, "w") as f:
            f.write(directory)
    except Exception:
        pass


# --- Despacho por version (logica de deteccion) ----------------------------
def parse_xml_file_by_version(xml_file_path):
    """
    Lee el XML para determinar su version CFDI y llama al parser apropiado.
    Detecta tambien si es un CFDI de Pagos 2.0.

    Devuelve un dict (Invoice/Nomina), una lista de dicts (Pagos) o None.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        cfdi_version = root.get("Version")
        tipo_comprobante = root.get("TipoDeComprobante")

        # Priorizar deteccion de Pagos 2.0
        if tipo_comprobante == "P" and cfdi_version == "4.0":
            return parse_cfdi_pago_20(xml_file_path)
        elif cfdi_version == "3.3":
            return parse_cfdi_33_invoice(xml_file_path)
        elif cfdi_version == "4.0":
            return parse_cfdi_40_invoice(xml_file_path)
        else:
            return None
    except ET.ParseError:
        return None
    except Exception:
        return None


def process_zip_file(zip_path):
    """Extrae los XMLs de un .zip a una carpeta temporal y los procesa."""
    temp_dir = tempfile.mkdtemp()
    extracted_data = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        for root_dir, _, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(".xml"):
                    xml_path = os.path.join(root_dir, file)
                    data = parse_xml_file_by_version(xml_path)
                    if data:
                        if isinstance(data, list):
                            extracted_data.extend(data)
                        else:
                            extracted_data.append(data)
    finally:
        shutil.rmtree(temp_dir)  # Limpiar archivos temporales
    return extracted_data


# --- Resultado del procesamiento -------------------------------------------
class ProcessResult:
    """Contenedor simple con los datos parseados y sus contadores."""

    def __init__(self):
        self.all_parsed_data = []
        self.invoice_data = []
        self.nomina_data = []
        self.pagos_data = []
        self.processed_count = 0
        self.error_count = 0

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
        return result

    targets = _collect_target_files(input_folder)
    total = len(targets)
    log(f"Escaneando directorio: {input_folder} ({total} archivo(s) encontrados)")

    for index, path in enumerate(targets, start=1):
        file = os.path.basename(path)
        if on_progress:
            on_progress(index, total, file)

        lower = file.lower()
        if lower.endswith(".xml"):
            log(f" - Procesando {file}...")
            parsed_data = parse_xml_file_by_version(path)
            if parsed_data:
                if isinstance(parsed_data, list):
                    result.all_parsed_data.extend(parsed_data)
                    result.processed_count += len(parsed_data)
                else:
                    result.all_parsed_data.append(parsed_data)
                    result.processed_count += 1
            else:
                result.error_count += 1
        elif lower.endswith(".zip"):
            log(f" - Descomprimiendo y procesando {file}...")
            zip_results = process_zip_file(path)
            if zip_results:
                result.all_parsed_data.extend(zip_results)
                result.processed_count += len(zip_results)

    # Separar por tipo para las hojas del Excel.
    result.invoice_data = [
        d for d in result.all_parsed_data if d.get("CFDI_Type") == "Invoice"]
    result.nomina_data = [
        d for d in result.all_parsed_data if d.get("CFDI_Type") == "Nomina"]
    result.pagos_data = [
        d for d in result.all_parsed_data if d.get("CFDI_Type") == "Pago"]

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
    """Exporta el ProcessResult a un archivo Excel multi-hoja."""
    export_to_excel(result.invoice_data, result.nomina_data,
                    result.pagos_data, output_path)


def open_file(path):
    """Abre un archivo con la aplicacion por defecto del sistema operativo."""
    if platform.system() == "Windows":
        os.startfile(path)  # noqa: P204 (API de Windows)
    else:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        subprocess.call([opener, path])
