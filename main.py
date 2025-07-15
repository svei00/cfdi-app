# --- cfdi_processor/main.py ---
# This file handles the main application flow, including directory input and calling other modules.
import platform
import os
# Used only to get the root for version detection
import xml.etree.ElementTree as ET
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# Import specific parsers based on CFDI version
from xml_parser_33 import parse_cfdi_33_invoice
from xml_parser_40 import parse_cfdi_40_invoice
from excel_exporter import export_to_excel
# Import from constants for file naming logic
from constants import INVOICE_COLUMN_ORDER

# Define the base directories where the XMLs will be stored and processed.
# These paths are now defined relative to a conceptual "AdminXML" folder located two levels up
# from where the script is run (e.g., if script is in AdminXML/CFDI_Processor_App, this points to AdminXML).
BASE_APP_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "AdminXML"))
# Adjusted to BovedaCFDI as per user's preference
BOVEDA_XML_DIR = os.path.join(BASE_APP_DIR, "BovedaCFDI")
REPORTS_DIR = os.path.join(BASE_APP_DIR, "Reports")

# File to store the last used directory for persistence
LAST_USED_DIR_FILE = os.path.join(REPORTS_DIR, "last_used_directory.txt")


def clear_terminal():
    """Clear the terminal screen based on the operating system."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def create_initial_directories():
    """Create the base application directories if they do not exist."""
    # Ensure the BASE_APP_DIR and its subdirectories exist
    os.makedirs(BASE_APP_DIR, exist_ok=True)
    os.makedirs(BOVEDA_XML_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    print(
        f"Ensured base directories exist: {BOVEDA_XML_DIR} and {REPORTS_DIR}")


def select_xml_directory_gui(title_text="Select XMLs Folder"):
    """
    Opens a GUI file dialog for the user to select a directory.
    Ensures the dialog appears in the foreground.
    Remembers the last used directory, or defaults to BOVEDA_XML_DIR.

    Args:
        title_text (str): The title to display on the dialog window.

    Returns:
        str: The selected directory path, or an empty string if cancelled.
    """
    # Determine initial directory for the file dialog
    # Default to the application's intended Boveda_XMLs path, resolved to absolute
    # This is already an absolute path due to os.path.abspath above
    initial_dir_to_use = BOVEDA_XML_DIR

    # Try to read the last used directory from file
    if os.path.exists(LAST_USED_DIR_FILE):
        try:
            with open(LAST_USED_DIR_FILE, 'r') as f:
                last_dir = f.read().strip()
                if os.path.isdir(last_dir):  # Check if the read directory is valid
                    initial_dir_to_use = last_dir
        except Exception as e:
            print(f"Error reading last used directory: {e}")

    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Bring the window to front (platform dependent)
    root.attributes('-topmost', True)  # For Windows/macOS
    root.lift()  # For X11 systems
    root.focus_force()  # Ensure focus

    messagebox.showinfo(
        "Folder Selection",
        "A folder selection window will now appear. Please select the directory containing your XML files."
    )

    selected_directory = filedialog.askdirectory(
        initialdir=initial_dir_to_use,  # Use the determined initial directory
        title=title_text
    )

    root.destroy()  # Destroy the Tkinter root window after selection

    # Save the selected directory for future use if it's not empty
    if selected_directory:
        try:
            # Ensure the REPORTS_DIR exists before trying to write the file
            # REPORTS_DIR is already an absolute path
            os.makedirs(REPORTS_DIR, exist_ok=True)
            with open(LAST_USED_DIR_FILE, 'w') as f:
                f.write(selected_directory)
        except Exception as e:
            print(f"Error saving last used directory: {e}")

    return selected_directory


def select_file_save_path_gui(initial_dir=".", default_filename="CFDI_Export.xlsx", title_text="Save Excel Report As"):
    """
    Opens a GUI file dialog for the user to select where to save the Excel file.
    Ensures the dialog appears in the foreground.

    Args:
        initial_dir (str): The directory to open the dialog in initially.
        default_filename (str): The default filename to suggest.
        title_text (str): The title to display on the dialog window.

    Returns:
        str: The selected file path, or an empty string if cancelled.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Bring the window to front (platform dependent)
    root.attributes('-topmost', True)  # For Windows/macOS
    root.lift()  # For X11 systems
    root.focus_force()  # Ensure focus

    messagebox.showinfo(
        "Save File Location",
        f"A file save window will now appear. Please select where to save your Excel report.\nSuggested filename: {default_filename}"
    )

    file_path = filedialog.asksaveasfilename(
        initialdir=initial_dir,
        initialfile=default_filename,
        title=title_text,
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )

    root.destroy()  # Destroy the Tkinter root window after selection
    return file_path


def determine_file_naming_components(parsed_data_list):
    """
    Determines the RFC, TypeOfXML (Emitidas/Recibidas/Mixed), and Year_Month for filename.
    Handles different date formats for parsing.

    Priority Logic:
    1. If invoices exist -> use invoices logic
    2. If no invoices but nominas exist -> use nominas logic
    3. Special nomina case: If only nominas with single RFC Emisor and single RFC Receptor -> Recibidas (employee scenario)
    """
    if not parsed_data_list:
        return "Generic", "Report", "UnknownDate"

    # Separate regular invoices from nominas for primary RFC/date collection
    invoice_data = [d for d in parsed_data_list if d.get(
        "CFDI_Type") == "Invoice"]
    nomina_data = [d for d in parsed_data_list if d.get(
        "CFDI_Type") == "Nomina"]

    all_rfcs_emisor = set()
    all_rfcs_receptor = set()
    all_dates_set = set()  # Store (year, month) tuples

    # Helper function to parse date strings with multiple formats
    def parse_date_string(date_str_val):
        if not date_str_val:
            return None

        # Try the full timestamp format first (for Fecha Timbrado)
        try:
            return datetime.strptime(date_str_val, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            pass

        # If that fails, try the date-only format (for Fecha Emision)
        try:
            return datetime.strptime(date_str_val, "%d/%m/%Y")
        except ValueError:
            pass

        return None  # Return None if neither format matches

    # Collect RFCs and Dates from ALL parsed data (invoices and nominas)
    for data in parsed_data_list:
        emisor_rfc = data.get("RFC Emisor")
        receptor_rfc = data.get("RFC Receptor")

        if emisor_rfc:
            all_rfcs_emisor.add(emisor_rfc)
        if receptor_rfc:
            all_rfcs_receptor.add(receptor_rfc)

        # Extract dates (Fecha Emision prioritized)
        date_str = data.get("Fecha Emision")
        if not date_str:  # Fallback to Fecha Timbrado if Fecha Emision is not available
            date_str = data.get("Fecha Timbrado")

        dt_object = parse_date_string(date_str)
        if dt_object:
            all_dates_set.add((dt_object.year, dt_object.month))

    # --- REVISED RFC AND TYPE NAMING LOGIC ---
    rfc_part = "MixedRFCs"
    type_of_xml_part = "Report"

    if len(all_rfcs_emisor) == 1:
        # If there's only one unique Emisor RFC across all documents
        dominant_rfc = list(all_rfcs_emisor)[0]
        rfc_part = dominant_rfc
        type_of_xml_part = "Emitidas"

        # Special check for Nomina: if it's a single Emisor and single Receptor,
        # and they are different, it's likely a "Recibidas" scenario for the employee.
        if len(all_rfcs_receptor) == 1 and list(all_rfcs_receptor)[0] != dominant_rfc and nomina_data and not invoice_data:
            rfc_part = list(all_rfcs_receptor)[0]
            type_of_xml_part = "Recibidas"

    elif len(all_rfcs_receptor) == 1:
        # If there's only one unique Receptor RFC across all documents
        dominant_rfc = list(all_rfcs_receptor)[0]
        rfc_part = dominant_rfc
        type_of_xml_part = "Recibidas"
    else:
        # If neither of the above, it's a mixed scenario.
        # If there's only one unique RFC overall (Emisor or Receptor), use that as the RFC part.
        unique_combined_rfcs = all_rfcs_emisor.union(all_rfcs_receptor)
        if len(unique_combined_rfcs) == 1:
            rfc_part = list(unique_combined_rfcs)[0]
            type_of_xml_part = "Mixed"  # Still "Mixed" as it's not purely Emitidas/Recibidas

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
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        cfdi_version = root.get('Version')

        if cfdi_version == '3.3':
            return parse_cfdi_33_invoice(xml_file_path)
        elif cfdi_version == '4.0':
            return parse_cfdi_40_invoice(xml_file_path)
        else:
            print(
                f"Error: CFDI version '{cfdi_version}' not supported for {os.path.basename(xml_file_path)}. Skipping file.")
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

    print("------ CFDI Invoice Processing Application ------")
    print("This tool will parse XML electronic invoices from a specified directory and export the data to an Excel file.")
    print("It automatically detects if an XML is a regular CFDI or a Nomina Complement.")
    print("\nFuture enhancements will include a GUI and automated XML download from SAT using tools like Selenium or Scrapy.")
    print("--------------------------------------------------\n")

    create_initial_directories()

    input_folder = ""
    # Use GUI for selecting the input XML folder.
    input_folder = select_xml_directory_gui(
        title_text="Select CFDI XMLs Folder"
    )
    if not input_folder:  # If user closed the GUI dialog or cancelled
        print("No folder selected via GUI. Exiting.")
        return  # Exit if no folder selected

    if not os.path.isdir(input_folder):
        print(
            f"Error: The provided path '{input_folder}' is not a valid directory.")
        return

    all_parsed_data = []
    processed_count = 0
    error_count = 0

    print(f"\nScanning directory: {input_folder}")
    for root_dir, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(".xml"):
                xml_file_path = os.path.join(root_dir, file)
                print(f" - Processing {file}...")
                # Call the version dispatcher function
                parsed_data = parse_xml_file_by_version(xml_file_path)
                if parsed_data:
                    all_parsed_data.append(parsed_data)
                    processed_count += 1
                else:
                    error_count += 1

    if not all_parsed_data:
        print("No valid CFDI XML files were processed. Please check the directory and file formats.")
        return

    # Separate data for different sheets.
    invoice_data = [d for d in all_parsed_data if d.get(
        "CFDI_Type") == "Invoice"]
    nomina_data = [d for d in all_parsed_data if d.get(
        "CFDI_Type") == "Nomina"]

    print(
        f"\nProcessed {processed_count} XML files. ({error_count} errors encountered.)")
    print(f"Found {len(invoice_data)} CFDI Electronic Invoices.")
    print(f"Found {len(nomina_data)} CFDI Nomina complement.\n")

    # Determine dynamic filename components
    rfc_part, type_part, date_part = determine_file_naming_components(
        all_parsed_data)
    dynamic_default_excel_filename = f"{rfc_part}_{type_part}_{date_part}.xlsx"

    # Use GUI for saving the Excel file
    excel_output_path = select_file_save_path_gui(
        initial_dir=REPORTS_DIR,  # Suggest REPORTS_DIR as initial directory
        default_filename=dynamic_default_excel_filename,
        title_text="Save CFDI Excel Report"
    )

    if not excel_output_path:
        print("No output file path selected. Exiting.")
        return

    # Export to Excel with separate sheets.
    export_to_excel(invoice_data, nomina_data, excel_output_path)

    print(f"\nProcessing complete. Check the output folder for your Excel report.")
    print(f"Output saved at: {excel_output_path}")


if __name__ == "__main__":
    main()
