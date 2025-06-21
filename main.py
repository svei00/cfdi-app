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

# Define the base directory where the XMLs will be stored and processed
BASE_APP_DIR = "CFDI_Processor_App"
BOVEDA_XML_DIR = os.path.join(BASE_APP_DIR, "Boveda_XMLs")
REPORTS_DIR = os.path.join(BASE_APP_DIR, "Reports")


def clear_terminal():
    """Clear the terminal screen based on the operating system."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def create_initial_directories():
    """Create the base application directories if they do not exist."""
    os.makedirs(BOVEDA_XML_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    print(
        f"Ensured base directories exist: {BASE_APP_DIR}/Boveda_XMLs and {BASE_APP_DIR}/Reports")


def select_xml_directory_gui(initial_dir=".", title_text="Select XMLs Folder"):
    """
    Opens a GUI file dialog for the user to select a directory.
    Ensures the dialog appears in the foreground.

    Args:
        initial_dir (str): The directory to open the dialog in initially.
        title_text (str): The title to display on the dialog window.

    Returns:
        str: The selected directory path, or an empty string if cancelled.
    """
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
        initialdir=initial_dir,
        title=title_text
    )

    root.destroy()  # Destroy the Tkinter root window after selection
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
    Considers the entire list of parsed data.
    """
    if not parsed_data_list:
        return "Generic", "Report", "UnknownDate"

    all_rfcs_emisor = set()
    all_rfcs_receptor = set()
    all_dates_set = set()  # Store (year, month) tuples

    for data in parsed_data_list:
        emisor_rfc = data.get("RFC Emisor")
        receptor_rfc = data.get("RFC Receptor")

        if emisor_rfc:
            all_rfcs_emisor.add(emisor_rfc)
        if receptor_rfc:
            all_rfcs_receptor.add(receptor_rfc)

        # Extract date for month/year (prioritize Fecha Emision if available, else Fecha Timbrado)
        # Dates are parsed in xml_parser to "DD/MM/YYYY HH:MM:SS" for Fecha Timbrado
        # and "DD/MM/YYYY" for Fecha Emision. Need to handle both for robustness here.
        date_str = data.get("Fecha Emision")  # Preferred for date part
        if not date_str:
            date_str = data.get("Fecha Timbrado")  # Fallback

        if date_str:
            try:
                # Attempt to parse as datetime object
                dt_object = None
                if 'T' in date_str:  # Original XML format "YYYY-MM-DDTHH:MM:SS"
                    dt_object = datetime.strptime(
                        date_str, "%Y-%m-%dT%H:%M:%S")
                elif ':' in date_str:  # Formatted with time "DD/MM/YYYY HH:MM:SS"
                    dt_object = datetime.strptime(
                        date_str, "%d/%m/%Y %H:%M:%S")
                elif '/' in date_str:  # Formatted without time "DD/MM/YYYY"
                    dt_object = datetime.strptime(date_str, "%d/%m/%Y")

                if dt_object:
                    all_dates_set.add((dt_object.year, dt_object.month))
            except ValueError:
                pass  # Ignore malformed dates

    # Determine RFC part and TypeOfXML part based on user's refined logic
    rfc_part = "MixedRFCs"
    # Default fallback for truly mixed or undeterminable cases
    type_of_xml_part = "Report"

    # Scenario 1: All documents are emitted by a single, consistent RFC.
    # This means: all RFCs in 'all_rfcs_emisor' are the same, and any RFCs in 'all_rfcs_receptor' are NOT this dominant RFC.
    # Also, ensure there are actual 'Emitidas' documents (i.e., not just an empty set of emitters)
    if len(all_rfcs_emisor) == 1:
        dominant_emisor_rfc = list(all_rfcs_emisor)[0]
        is_truly_emitidas = True

        # Check if this dominant_emisor_rfc ever acts as a receptor for any document in the list
        for data in parsed_data_list:
            if data.get("RFC Receptor") == dominant_emisor_rfc and data.get("RFC Emisor") != dominant_emisor_rfc:
                is_truly_emitidas = False
                break

        # Also check if any Nomina document exists where the dominant_emisor_rfc is the emisor.
        # If so, it should be Emitidas.
        # has_nomina_for_dominant_emisor = any(
        #     data.get("CFDI_Type") == "Nomina" and data.get(
        #         "RFC Emisor") == dominant_emisor_rfc
        #     for data in parsed_data_list
        # )

        # if is_truly_emitidas or has_nomina_for_dominant_emisor:
        #     rfc_part = dominant_emisor_rfc
        #     type_of_xml_part = "Emitidas"

    # Scenario 2: All documents are received by a single, consistent RFC.
    # This means: all RFCs in 'all_rfcs_receptor' are the same, and any RFCs in 'all_rfcs_emisor' are NOT this dominant RFC.
    # AND no Nomina documents exist for this dominant RFC.
    # Only proceed if not already determined as Emitidas
    if rfc_part == "MixedRFCs" and len(all_rfcs_receptor) == 1:
        dominant_receptor_rfc = list(all_rfcs_receptor)[0]
        is_truly_recibidas = True

        # Check if this dominant_receptor_rfc ever acts as an emisor for any document in the list
        # or if there are any Nomina documents where it's the emisor (Nomina implies Emitidas)
        for data in parsed_data_list:
            if data.get("RFC Emisor") == dominant_receptor_rfc:
                is_truly_recibidas = False
                break

        if is_truly_recibidas:
            rfc_part = dominant_receptor_rfc
            type_of_xml_part = "Recibidas"

    # Scenario 3: If neither of the above determined a clear RFC and type, check for a single RFC in mixed roles.
    # If there's exactly one RFC that shows up in either Emisor or Receptor, it's a "Mixed" report for that RFC.
    combined_unique_rfcs = all_rfcs_emisor.union(all_rfcs_receptor)
    if rfc_part == "MixedRFCs" and len(combined_unique_rfcs) == 1:
        dominant_rfc = list(combined_unique_rfcs)[0]
        rfc_part = dominant_rfc
        type_of_xml_part = "Mixed"  # It's mixed because it wasn't purely Emitidas or Recibidas

    # Final fallback for type_of_xml_part if still "Report"
    if type_of_xml_part == "Report" and rfc_part != "MixedRFCs":
        # If RFC is determined but type is not, it's mixed.
        type_of_xml_part = "Mixed"

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

        # If multiple dates, express as a range (e.g., 202401-202403)
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
    # Use GUI for selecting the input XML folder
    input_folder = select_xml_directory_gui(
        initial_dir=BOVEDA_XML_DIR,
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
