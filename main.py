# --- cfdi_processor/main.py ---
# This file handles the main application flow, including directory input and calling other modules.
import platform
import os
from xml_parser import parse_xml_invoice
from excel_exporter import export_to_excel
from datetime import datetime
import tkinter as tk  # Import tkinter for GUI file dialog
# Import filedialog and messagebox for user interaction
from tkinter import filedialog, messagebox

# Define the base directory where the XMLs will be stored and processed
# User can change the directory path as needed
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

    Args:
        initial_dir (str): The directory to open the dialog in initially.
        title_text (str): The title to display on the dialog window.

    Returns:
        str: The selected directory path, or an empty string if cancelled.
    """
    # Create a Tkinter root window but hide it
    root = tk.Tk()
    root.withdraw()

    # Show a message box to inform the user about the upcoming file dialog
    messagebox.showinfo(
        "Folder Selection",
        "A folder selection window will now appear. Please select the directory containing your XML files."
    )

    # Open the directory selection dialog
    selected_directory = filedialog.askdirectory(
        initialdir=initial_dir,
        title=title_text
    )

    # Destroy the Tkinter root window after selection
    root.destroy()
    return selected_directory


def main():
    """
    Main function to process the CFDI XML processing application.
    """

    # Clear the terminal for a fresh start.
    clear_terminal()

    print("------ CFDI Invoice Processing Application ------")
    print("This tool will parse XML electronic invoices from a specified directory and export the data to an Excel file.")
    print("It automatically detects if an XML is a regular CFDI or a Nomina Complement.")
    print("\nFuture enhancements will include a GUI and automated XML download from SAT using tools like Selenium or Scrapy.")
    print("--------------------------------------------------\n")

    create_initial_directories()

    input_folder = ""
    # Offer GUI option
    use_gui = input(
        "Do you want to use a graphical interface to select the XML folder? (yes/no): ").lower().strip()

    if use_gui == 'yes':
        input_folder = select_xml_directory_gui(
            initial_dir=BOVEDA_XML_DIR,
            title_text="Select CFDI XMLs Folder"
        )
        if not input_folder:  # If user closed the GUI dialog
            print("No folder selected via GUI. Falling back to command-line input.")
            input_folder = input(
                f"\nEnter the path of the folder containing your XML files (e.g., '{BOVEDA_XML_DIR}/RFC/Emitidas/2025/07'): \n").strip()
    else:
        input_folder = input(
            f"\nEnter the path of the folder containing your XML files (e.g., '{BOVEDA_XML_DIR}/RFC/Emitidas/2025/07'): \n").strip()

    if not input_folder:
        print("No input folder provided. Exiting.")
        return

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

    # User Input for Excel output export.
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_excel_filename = f"CFDI_Export_{current_time}.xlsx"
    default_excel_output_path = os.path.join(
        REPORTS_DIR, default_excel_filename)

    excel_output_path = input(
        f"Enter the desired path for the Excel output file (default: {default_excel_output_path}): \n").strip()
    if not excel_output_path:
        excel_output_path = default_excel_output_path

    # Export to Excel with separate sheets.
    export_to_excel(invoice_data, nomina_data, excel_output_path)

    print(f"\nProcessing complete. Check the output folder for your Excel report.")
    print(f"Output saved at: {excel_output_path}")


if __name__ == "__main__":
    main()
