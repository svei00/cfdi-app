# --- cfdi_processor/main.py ---
# This file handles the main application flow, including directory input and calling other modules.
import platform
import os
# Assuming xml_parser has been fixed in previous steps
from xml_parser import parse_xml_invoice
from excel_exporter import export_to_excel
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# Define the base directories where the XMLs will be stored and processed.
# These paths are now relative to the current working directory of the script.
# BASE_APP_DIR = "CFDI_Processor_App"
BASE_APP_DIR = "../../AdminXML"
BOVEDA_XML_DIR = os.path.join(BASE_APP_DIR, "BovedaCFDI")
REPORTS_DIR = os.path.join(BASE_APP_DIR, "Reports")

# File to store the last used directory for persistence
# This file will be stored within the REPORTS_DIR
LAST_USED_DIR_FILE = os.path.join(REPORTS_DIR, "last_used_directory.txt")
os.system(f"attrib +h {LAST_USED_DIR_FILE}")


def clear_terminal():
    """Clear the terminal screen based on the operating system."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def create_initial_directories():
    """Create the base application directories if they do not exist."""
    # Ensure the parent application directory exists first, then its subdirectories
    os.makedirs(os.path.abspath(BASE_APP_DIR), exist_ok=True)
    # Ensure absolute path is created
    os.makedirs(os.path.abspath(BOVEDA_XML_DIR), exist_ok=True)
    # Ensure absolute path is created
    os.makedirs(os.path.abspath(REPORTS_DIR), exist_ok=True)
    print(
        f"Ensured base directories exist: {os.path.abspath(BOVEDA_XML_DIR)} and {os.path.abspath(REPORTS_DIR)}")


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
    initial_dir_to_use = os.path.abspath(BOVEDA_XML_DIR)

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
            # os.path.abspath(REPORTS_DIR) ensures the path is fully resolved before os.makedirs
            os.makedirs(os.path.abspath(REPORTS_DIR), exist_ok=True)
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

    Priority Logic (as provided by user from Claude 4.0 and further refined):
    1. If invoices exist -> use invoices logic (to populate RFCs/dates)
    2. If no invoices but nominas exist -> use nominas logic (to populate RFCs/dates)
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

    # PRIORITY 1: Collect RFCs and Dates from Invoices AND Nomina (if invoices exist)
    # This block populates all_rfcs_emisor, all_rfcs_receptor based on ALL documents (invoices and nominas)
    # if there are ANY invoices present.
    if invoice_data:
        for data in parsed_data_list:  # Iterate over all parsed data, not just invoices
            emisor_rfc = data.get("RFC Emisor")
            receptor_rfc = data.get("RFC Receptor")

            if emisor_rfc:
                all_rfcs_emisor.add(emisor_rfc)
            if receptor_rfc:
                all_rfcs_receptor.add(receptor_rfc)

            # Extract dates (Fecha Emision prioritized)
            date_str = data.get("Fecha Emision") or data.get("Fecha Timbrado")
            if date_str:
                try:
                    dt_object = None
                    if 'T' in date_str and len(date_str) == 19:
                        dt_object = datetime.strptime(
                            date_str, "%Y-%m-%dT%H:%M:%S")
                    elif ':' in date_str and len(date_str) > 10:
                        dt_object = datetime.strptime(
                            date_str, "%d/%m/%Y %H:%M:%S")
                    elif '/' in date_str and len(date_str) == 10:
                        dt_object = datetime.strptime(date_str, "%d/%m/%Y")

                    if dt_object:
                        all_dates_set.add((dt_object.year, dt_object.month))
                except ValueError:
                    pass

    # PRIORITY 2: If no invoices, use nominas only for RFC and date collection
    elif nomina_data:
        for data in nomina_data:  # Only iterate over nomina data if no invoices
            emisor_rfc = data.get("RFC Emisor")
            receptor_rfc = data.get("RFC Receptor")

            if emisor_rfc:
                all_rfcs_emisor.add(emisor_rfc)
            if receptor_rfc:
                all_rfcs_receptor.add(receptor_rfc)

            # Extract dates (Fecha Emision prioritized)
            date_str = data.get("Fecha Emision") or data.get("Fecha Timbrado")
            if date_str:
                try:
                    dt_object = None
                    if 'T' in date_str:
                        dt_object = datetime.strptime(
                            date_str, "%Y-%m-%dT%H:%M:%S")
                    elif ':' in date_str:
                        dt_object = datetime.strptime(
                            date_str, "%d/%m/%Y %H:%M:%S")
                    elif '/' in date_str:
                        dt_object = datetime.strptime(date_str, "%d/%m/%Y")

                    if dt_object:
                        all_dates_set.add((dt_object.year, dt_object.month))
                except ValueError:
                    pass

        # Special nomina logic (ONLY if no invoices and only nomina data processed)
        # If there's exactly one Emisor RFC and exactly one Receptor RFC among nominas,
        # it implies an employee receiving salary. The main RFC for the report
        # should be the RECEPTOR RFC.
        if len(all_rfcs_emisor) == 1 and len(all_rfcs_receptor) == 1:
            temp_emisor_rfc = list(all_rfcs_emisor)[0]
            temp_receptor_rfc = list(all_rfcs_receptor)[0]

            # If the single Emisor is NOT the same as the single Receptor (typical employee scenario)
            if temp_emisor_rfc != temp_receptor_rfc:
                all_rfcs_emisor = set()  # Clear Emisor set
                # Keep only the Receptor RFC as the "dominant" one
                all_rfcs_receptor = {temp_receptor_rfc}
            # If emisor and receptor are the same (self-issued/mixed for other reasons), treat as mixed later

    # Determine RFC part and TypeOfXML part
    rfc_part = "MixedRFCs"
    type_of_xml_part = "Report"

    # Scenario 1: All documents are emitted by a single, consistent RFC (Emitidas)
    # This is true if, after initial data collection, there's only one unique RFC in all_rfcs_emisor set.
    if len(all_rfcs_emisor) == 1:
        dominant_rfc = list(all_rfcs_emisor)[0]
        rfc_part = dominant_rfc
        type_of_xml_part = "Emitidas"
    # Scenario 2: All documents are received by a single, consistent RFC (Recibidas)
    # This is an 'elif' to ensure Emitidas takes priority if both sets happen to have 1 RFC.
    elif len(all_rfcs_receptor) == 1:
        dominant_rfc = list(all_rfcs_receptor)[0]
        rfc_part = dominant_rfc
        type_of_xml_part = "Recibidas"
    else:
        # Scenario 3: Single RFC in mixed roles, or truly mixed RFCs
        # If no single dominant RFC for Emisor or Receptor, check the union.
        unique_combined_rfcs = all_rfcs_emisor.union(all_rfcs_receptor)
        if len(unique_combined_rfcs) == 1:
            dominant_rfc = list(unique_combined_rfcs)[0]
            rfc_part = dominant_rfc
            # A single RFC, but it's not purely Emisor or Receptor based on initial checks
            type_of_xml_part = "Mixed"
        # If len(unique_combined_rfcs) > 1, then rfc_part remains "MixedRFCs" and type_of_xml_part remains "Report"

    # Determine Year_Month part
    year_month_part = "UnknownDate"
    if len(all_dates_set) == 1:
        year, month = list(all_dates_set)[0]
        year_month_part = f"{year}_{month:02d}"
    elif len(all_dates_set) > 1:
        # Get min and max year-month for a range
        sorted_dates = sorted(list(all_dates_set))
        min_year, min_month = sorted_dates[0]
        max_year, max_month = sorted_dates[-1]

        # Updated MixedDates format with underscores
        year_month_part = f"MixedDates_{min_year}_{min_month:02d}-{max_year}_{max_month:02d}"

    return rfc_part, type_of_xml_part, year_month_part


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
                parsed_data = parse_xml_invoice(xml_file_path)
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
    print(f"Found {len(invoice_data)} CFDI 4.0 Electronic Invoices.")
    print(f"Found {len(nomina_data)} CFDI 4.0 Nomina complement 1.2.\n")

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
