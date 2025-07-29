# --- cfdi_processor/main.py ---
# Este archivo maneja el flujo principal de la aplicación, incluyendo la entrada de directorios
# y la llamada a otros módulos.
import platform
import os
import xml.etree.ElementTree as ET  # CORREGIDO: xml.etree.ElementTree
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# Importar parsers específicos basados en la versión del CFDI
from xml_parser_33 import parse_cfdi_33_invoice
from xml_parser_40 import parse_cfdi_40_invoice
# Nuevo import para el parser de Pagos 2.0
from pagos_parser_20 import parse_cfdi_pago_20
from excel_exporter import export_to_excel
# Importar de constants para la lógica de nombres de archivo
from constants import INVOICE_COLUMN_ORDER

# Definir los directorios base donde se almacenarán y procesarán los XML.
# Estas rutas se definen ahora de forma relativa a una carpeta conceptual "AdminXML"
# situada dos niveles por encima de donde se ejecuta el script
# (por ejemplo, si el script está en AdminXML/CFDI_Processor_App, esto apunta a AdminXML).
BASE_APP_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "AdminXML"))
# Ajustado a BovedaCFDI según la preferencia del usuario
BOVEDA_XML_DIR = os.path.join(BASE_APP_DIR, "BovedaCFDI")
REPORTS_DIR = os.path.join(BASE_APP_DIR, "Reports")

# Archivo para almacenar el último directorio utilizado para persistencia
LAST_USED_DIR_FILE = os.path.join(REPORTS_DIR, "last_used_directory.txt")


def clear_terminal():
    """Limpia la pantalla de la terminal según el sistema operativo."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def create_initial_directories():
    """Crea los directorios base de la aplicación si no existen."""
    # Asegurarse de que el BASE_APP_DIR y sus subdirectorios existan
    os.makedirs(BASE_APP_DIR, exist_ok=True)
    os.makedirs(BOVEDA_XML_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    print(
        f"Se aseguró que los directorios base existan: {BOVEDA_XML_DIR} y {REPORTS_DIR}")


def select_xml_directory_gui(title_text="Seleccionar Carpeta de XMLs"):
    """
    Abre un cuadro de diálogo de selección de archivos GUI para que el usuario seleccione un directorio.
    Asegura que el diálogo aparezca en primer plano.
    Recuerda el último directorio utilizado, o por defecto usa BOVEDA_XML_DIR.

    Args:
        title_text (str): El título a mostrar en la ventana del diálogo.

    Returns:
        str: La ruta del directorio seleccionado, o una cadena vacía si se cancela.
    """
    # Determinar el directorio inicial para el diálogo de archivos
    # Por defecto, la ruta prevista de la aplicación Boveda_XMLs, resuelta a absoluta
    # Esto ya es una ruta absoluta debido a os.path.abspath anterior
    initial_dir_to_use = BOVEDA_XML_DIR

    # Intentar leer el último directorio utilizado del archivo
    if os.path.exists(LAST_USED_DIR_FILE):
        try:
            with open(LAST_USED_DIR_FILE, 'r') as f:
                last_dir = f.read().strip()
                if os.path.isdir(last_dir):  # Verificar si el directorio leído es válido
                    initial_dir_to_use = last_dir
        except Exception as e:
            print(f"Error al leer el último directorio utilizado: {e}")

    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal

    # Poner la ventana al frente (depende de la plataforma)
    root.attributes('-topmost', True)  # Para Windows/macOS
    root.lift()  # Para sistemas X11
    root.focus_force()  # Asegurar el foco

    messagebox.showinfo(
        "Selección de Carpeta",
        "A continuación aparecerá una ventana de selección de carpeta. Por favor, selecciona el directorio que contiene tus archivos XML."
    )

    selected_directory = filedialog.askdirectory(
        initialdir=initial_dir_to_use,  # Usar el directorio inicial determinado
        title=title_text
    )

    root.destroy()  # Destruir la ventana raíz de Tkinter después de la selección

    # Guardar el directorio seleccionado para uso futuro si no está vacío
    if selected_directory:
        try:
            # Asegurarse de que REPORTS_DIR exista antes de intentar escribir el archivo
            # REPORTS_DIR ya es una ruta absoluta
            os.makedirs(REPORTS_DIR, exist_ok=True)
            with open(LAST_USED_DIR_FILE, 'w') as f:
                f.write(selected_directory)
        except Exception as e:
            print(f"Error al guardar el último directorio utilizado: {e}")

    return selected_directory


def select_file_save_path_gui(initial_dir=".", default_filename="CFDI_Export.xlsx", title_text="Guardar Informe de Excel Como"):
    """
    Abre un cuadro de diálogo de selección de archivos GUI para que el usuario seleccione dónde guardar el archivo de Excel.
    Asegura que el diálogo aparezca en primer plano.

    Args:
        initial_dir (str): El directorio donde se abrirá el diálogo inicialmente.
        default_filename (str): El nombre de archivo predeterminado a sugerir.
        title_text (str): El título a mostrar en la ventana del diálogo.

    Returns:
        str: La ruta del archivo seleccionado, o una cadena vacía si se cancela.
    """
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal

    # Poner la ventana al frente (depende de la plataforma)
    root.attributes('-topmost', True)  # Para Windows/macOS
    root.lift()  # Para sistemas X11
    root.focus_force()  # Asegurar el foco

    messagebox.showinfo(
        "Guardar Ubicación del Archivo",
        f"A continuación aparecerá una ventana para guardar archivos. Por favor, selecciona dónde guardar tu informe de Excel.\nNombre de archivo sugerido: {default_filename}"
    )

    file_path = filedialog.asksaveasfilename(
        initialdir=initial_dir,
        initialfile=default_filename,
        title=title_text,
        defaultextension=".xlsx",
        filetypes=[("Archivos de Excel", "*.xlsx"),
                   ("Todos los archivos", "*.*")]
    )

    root.destroy()  # Destruir la ventana raíz de Tkinter después de la selección
    return file_path


def determine_file_naming_components(parsed_data_list):
    """
    Determines the RFC, TypeOfXML (Emitidas/Recibidas/Mixed), and Year_Month for filename.
    This function restores the original, working RFC logic and ensures robust date parsing.

    Priority Logic for RFC and Type:
    1. Identify all unique Emisor and Receptor RFCs across all document types.
    2. Determine if the set of RFCs indicates a clear 'Emitidas' or 'Recibidas' scenario.
       - 'Emitidas': Only one unique Emisor RFC, and all documents are from that Emisor.
       - 'Recibidas': Only one unique Receptor RFC, and all documents are for that Receptor.
       - Special 'Recibidas' for Nomina: If only Nomina files, one Emisor (company) and one DIFFERENT Receptor (employee),
         then it's 'Recibidas' for the employee's RFC.
    3. If not a clear 'Emitidas' or 'Recibidas', check for a single unique RFC overall (mixed roles).
    4. Otherwise, default to 'MixedRFCs_Report'.
    """
    if not parsed_data_list:
        return "Generic", "Report", "UnknownDate"

    all_rfcs_emisor = set()
    all_rfcs_receptor = set()
    all_dates_set = set()  # Store (year, month) tuples

    # Helper function to parse date strings with multiple formats
    def parse_date_string(date_str_val):
        if not date_str_val:
            return None

        # Try CFDI date-time format (e.g., "2025-04-09T18:24:00")
        try:
            return datetime.strptime(date_str_val, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass

        # Try Fecha Timbrado format (DD/MM/YYYY HH:MM:SS)
        try:
            return datetime.strptime(date_str_val, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            pass

        # Try Fecha Emision format (DD/MM/YYYY)
        try:
            return datetime.strptime(date_str_val, "%d/%m/%Y")
        except ValueError:
            pass

        return None  # Return None if no format matches

    # Collect all RFCs and Dates from ALL parsed data
    for data in parsed_data_list:
        emisor_rfc = data.get("RFC Emisor") or data.get("RFC Emisor CFDI")
        receptor_rfc = data.get(
            "RFC Receptor") or data.get("RFC Receptor CFDI")

        if emisor_rfc:
            all_rfcs_emisor.add(emisor_rfc)
        if receptor_rfc:
            all_rfcs_receptor.add(receptor_rfc)

        # Prioritize Fecha Emision, then Fecha Timbrado, then FechaPago (for Pagos)
        date_str = data.get("Fecha Emision")
        if not date_str:
            date_str = data.get("Fecha Timbrado")
        if not date_str and data.get("CFDI_Type") == "Pago":
            # This is from the pago20:Pago node, not the comprobante.
            date_str = data.get("FechaPago")

        dt_object = parse_date_string(date_str)
        if dt_object:
            all_dates_set.add((dt_object.year, dt_object.month))

    # --- RFC AND TYPE NAMING LOGIC ---
    rfc_part = "MixedRFCs"
    type_of_xml_part = "Report"

    # Check for a single dominant Emisor RFC (Emitidas)
    if len(all_rfcs_emisor) == 1:
        dominant_rfc = list(all_rfcs_emisor)[0]
        # Check if this dominant Emisor RFC is also the *only* Receptor RFC.
        # This implies a self-issued or mixed role for a single entity.
        if len(all_rfcs_receptor) == 1 and list(all_rfcs_receptor)[0] == dominant_rfc:
            rfc_part = dominant_rfc
            type_of_xml_part = "Mixed"  # Single RFC acting as both Emisor and Receptor
        else:
            rfc_part = dominant_rfc
            type_of_xml_part = "Emitidas"  # Primarily emitting documents

    # If not a single dominant Emisor, check for a single dominant Receptor RFC (Recibidas)
    elif len(all_rfcs_receptor) == 1:
        dominant_rfc = list(all_rfcs_receptor)[0]
        rfc_part = dominant_rfc
        type_of_xml_part = "Recibidas"

        # Special case for Nomina: If it's primarily Nomina files with one Emisor and one DIFFERENT Receptor,
        # and the dominant RFC is the Receptor, it's still Recibidas for the employee.
        # This is already covered by the general 'Recibidas' logic if all_rfcs_receptor is 1.

    # If neither of the above, check if there's only one unique RFC overall (mixed roles for that single RFC)
    else:
        unique_combined_rfcs = all_rfcs_emisor.union(all_rfcs_receptor)
        if len(unique_combined_rfcs) == 1:
            rfc_part = list(unique_combined_rfcs)[0]
            type_of_xml_part = "Mixed"  # Single RFC involved in mixed roles
        # If still no clear dominant RFC, keep the initial "MixedRFCs_Report" default.

    # Determine Year_Month part
    year_month_part = "UnknownDate"
    if len(all_dates_set) == 1:
        year, month = list(all_dates_set)[0]
        year_month_part = f"{year}_{month:02d}"
    elif len(all_dates_set) > 1:
        sorted_dates = sorted(list(all_dates_set))
        min_year, min_month = sorted_dates[0]
        max_year, max_month = sorted_dates[-1]
        # If years are different, show the range of years
        if min_year != max_year:
            year_month_part = f"MixedDates_{min_year}-{max_year}"
        # If years are the same but months are different, show month range
        else:
            year_month_part = f"{min_year}_{min_month:02d}-{max_month:02d}"

    return rfc_part, type_of_xml_part, year_month_part


def parse_xml_file_by_version(xml_file_path):
    """
    Reads the XML file to determine its CFDI version and calls the appropriate parser.
    Also detects if it is a Pagos CFDI.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        cfdi_version = root.get('Version')
        tipo_comprobante = root.get('TipoDeComprobante')

        # Prioritize Pagos 2.0 detection
        if tipo_comprobante == 'P' and cfdi_version == '4.0':
            # It's a CFDI de Pagos 2.0
            return parse_cfdi_pago_20(xml_file_path)
        elif cfdi_version == '3.3':
            return parse_cfdi_33_invoice(xml_file_path)
        elif cfdi_version == '4.0':
            # It's a regular CFDI 4.0 (Ingreso, Egreso, Traslado, Nómina)
            return parse_cfdi_40_invoice(xml_file_path)
        else:
            print(
                f"Error: CFDI version '{cfdi_version}' or TipoDeComprobante '{tipo_comprobante}' not supported for {os.path.basename(xml_file_path)}. Skipping file.")
            return None
    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file_path}: {e}")
        return None
    except Exception as e:
        print(
            f"An unexpected error occurred while reading version from {xml_file_path}: {e}")
        return None


def main():
    """
    Main function to process the CFDI XML processing application.
    """
    clear_terminal()

    print("------ Aplicación de Procesamiento de Facturas CFDI ------")
    print("Esta herramienta analizará las facturas electrónicas XML de un directorio especificado y exportará los datos a un archivo de Excel.")
    print("Detecta automáticamente si un XML es un CFDI regular, un Complemento de Nómina o un Complemento de Pagos.")
    print("\nLas mejoras futuras incluirán una GUI y la descarga automatizada de XML desde el SAT utilizando herramientas como Selenium o Scrapy.")
    print("--------------------------------------------------\n")

    create_initial_directories()

    input_folder = ""
    # Use GUI for selecting the input XML folder.
    input_folder = select_xml_directory_gui(
        title_text="Seleccionar Carpeta de XMLs CFDI"
    )
    if not input_folder:  # If user closed the GUI dialog or cancelled
        print("No se seleccionó ninguna carpeta a través de la GUI. Saliendo.")
        return  # Exit if no folder selected

    if not os.path.isdir(input_folder):
        print(
            f"Error: La ruta proporcionada '{input_folder}' no es un directorio válido.")
        return

    all_parsed_data = []
    processed_count = 0
    error_count = 0

    print(f"\nEscaneando directorio: {input_folder}")
    for root_dir, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(".xml"):
                xml_file_path = os.path.join(root_dir, file)
                print(f" - Procesando {file}...")
                # Call the version dispatcher function
                parsed_data = parse_xml_file_by_version(xml_file_path)
                if parsed_data:
                    # parse_cfdi_pago_20 devuelve una LISTA de diccionarios, mientras que los otros devuelven un diccionario.
                    # Necesitamos aplanarlo si es una lista.
                    if isinstance(parsed_data, list):
                        all_parsed_data.extend(parsed_data)
                        processed_count += len(parsed_data)
                    else:
                        all_parsed_data.append(parsed_data)
                        processed_count += 1
                else:
                    error_count += 1

    if not all_parsed_data:
        print("No se procesaron archivos XML CFDI válidos. Por favor, verifica el directorio y los formatos de archivo.")
        return

    # Separar datos para diferentes hojas.
    invoice_data = [d for d in all_parsed_data if d.get(
        "CFDI_Type") == "Invoice"]
    nomina_data = [d for d in all_parsed_data if d.get(
        "CFDI_Type") == "Nomina"]
    pagos_data = [d for d in all_parsed_data if d.get(
        "CFDI_Type") == "Pago"]  # Nueva lista para datos de Pagos

    print(
        f"\nSe procesaron {processed_count} archivos XML. ({error_count} errores encontrados.)")
    print(f"Se encontraron {len(invoice_data)} Facturas Electrónicas CFDI.")
    print(
        f"Se encontraron {len(nomina_data)} Complementos de Nómina CFDI 1.2.")
    print(
        f"Se encontraron {len(pagos_data)} Complementos de Pagos CFDI 2.0.\n")

    # Determinar componentes dinámicos del nombre del archivo
    rfc_part, type_part, date_part = determine_file_naming_components(
        all_parsed_data)
    dynamic_default_excel_filename = f"{rfc_part}_{type_part}_{date_part}.xlsx"

    # Usar GUI para guardar el archivo de Excel
    excel_output_path = select_file_save_path_gui(
        initial_dir=REPORTS_DIR,  # Sugerir REPORTS_DIR como directorio inicial
        default_filename=dynamic_default_excel_filename,
        title_text="Guardar Informe de Excel CFDI"
    )

    if not excel_output_path:
        print("No se seleccionó ninguna ruta de archivo de salida. Saliendo.")
        return

    # Exportar a Excel con hojas separadas.
    # Ahora pasamos la nueva lista de datos de pagos
    export_to_excel(invoice_data, nomina_data, pagos_data, excel_output_path)

    print(f"\nProcesamiento completado. Revisa la carpeta de salida para tu informe de Excel.")
    print(f"Salida guardada en: {excel_output_path}")


if __name__ == "__main__":
    main()
