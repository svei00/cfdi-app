import pandas as pd
import os
# Import the xml_parser to acces its field list for column dropping.
import xml_parser


def export_to_excel(invoice_data_list, nomina_data_list, output_file_path):
    """
    Export list of dictionaris (one for invoices, one for nominas) to an Excel file
    with separate sheets using Pandas.

    Args:
        invoice_data_list (list): A list of dictionaries for regular invoices.
        nomina_data_list (list): List of dictionaries for nomina complement.
        output_file_path (str): The full path where the Excel file will be saved.
    """
    if not invoice_data_list and not nomina_data_list:
        print("No data to export. Excel file will not be created.")
        return

    # Adding the logic to handle if Windows just the letter of the drive.
    # Checks if the output_file_path is just a drive letter (ex. D:)
    # This assumes Windows path conventions (Drive letter followed by letter)
    if os.path.ismount(output_file_path) and len(output_file_path) == 2 and output_file_path[1] == ':':
        # If it's just a drive letter, append a default subfolder and filename
        # For example D:\CFDI_Exports\CFDI_Report.xlsx
        output_file_path = os.path.join(
            output_file_path, 'CFDI_Exports', 'CFDI_Report.xlsx')
        print(
            f"Warning: Output path was a Drive root. Adjust to: {output_file_path}")

    # Ensure output directory exists.
    # os.path.dirname gets the directory part of the path
    output_dir = os.path.dirname(output_file_path)
    # If output_file_path was just a filename (ex.  "report.xlsx"), output_dir is empty
    if not output_dir:
        # Fallback to a default reports folder relative to the current working directory
        output_dir = os.path.join(os.getcwd(), 'CFDI_Processor_App', "Reports")

    os.makedirs(output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
            if invoice_data_list:
                df_invoices = pd.DataFrame(invoice_data_list)
                # Define columns specific to Nomina that should be dropped from Invoice sheet.
                nomina_cols_to_drop = [
    os.makedirs(output_dir, exist_ok=True)

    try:
    # Ensure output directory exists.
    output_dir = os.path.dirname(output_file_path)
    os.makedirs(output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
            if invoice_data_list:
                df_invoices = pd.DataFrame(invoice_data_list)

                # Reorder columns for invoices sheets based on INVOICE_COLUMN_ORDER
                # Ensures all columns in that list are present, fill with None if missing.
                final_invoice_columns = [] # List where we'll parsing data.
                for col in xml_parser.INVOICE_COLUMN_ORDER:
                    if col in df_invoices.columns:
                        final_invoice_columns.append(col)
                    else:
                        df_invoices[col] = None

                df_invoices = df_invoices[final_invoice_columns] # Apply the order

                # Define columns specific to Nomina that should be dropped from Invoice sheet.
                nomina_cols_to_drop = [
                    col_name for _, _, _, col_name in xml_parser.NOMINA_FIELDS_TO_EXTRACT]
                nomina_cols_to_drop.extend(
                    ['TotalGravado', 'TotalExento', 'TotalDeducciones', 'TotalOtrosPagos'])

                # # Define columns specific to ImpLocal that should be dropped from Nomina sheet.
                # implocal_cols_to_drop = [
                #     "ImpLocal_TotalRetenciones",
                #     "ImpLocal_TotalTraslados",
                #     "ImpLocal_TrasladadosLocales_Details",
                # ]

                # Drop nomina-specific columns from invoice dataframe.
                df_invoices = df_invoices.drop(columns=[
                                               col for col in nomina_cols_to_drop if col in df_invoices.columns and column not in xml_parser.INVOICE_COLUMN_ORDER
                                               ], errors='ignore')
                # Drop the type column.
                # Drop the internal "CFDI_Type" and "ImpLocal_TrasladosLocales_Details (If it is for internal use)"
                df_invoices = df_invoices.drop(
                    columns=['CFDI_Type', 'ImpLocal_TrasladosLocales_Details'], errors='ignore')

                df_invoices.to_excel(
                    writer, sheet_name='Invoices', index=False)
                print(
                    f"Exported {len(invoice_data_list)} regular CFDI invoices to 'Invoices' sheet.")
            else:
                print("No Invoice data to export.")

            # Nomina 1.2
            if nomina_data_list:
                df_nominas = pd.DataFrame(nomina_data_list)

                # Define a more explicit set of columns to KEEP for the nominas sheet
                # These are core CFDI fields plus all Nomina-specific fields.
                nomina_column_order = [
                    "Factura", "UUID", "RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
                    "Total", "Moneda", "Tipo De Cambio", "Condicion de Pago", "FormaDePago", "Metodo de Pago",
                    "Version Nomina", "Tipo Nomina", "Fecha Pago", "Fecha Inicial Pago", "Fecha Final Pago",
                    "Total Sueldos", "Total Deducciones", "Total Otros Pagos", "Registro Patronal",
                    "CURP Patron", "RFC Patron", "CURP", "NSS", "Inicio Relacion Laboral", "Antiguedad",
                    "Periodicidad Pago", "SBC", "SDI", "Entidad", "TotalGravado", "TotalExcento",
                    # Add Complemento to Nomina for context
                    "ImpuestosRetenidos", "Archivo XML", "Complemento"
                ]

                # Ensure all desired colums are present, fill with none if missing
                final_nomina_columns[]
                for col in nomina_colum_order:
                    if col in df_nominas.columns:
                        final_nomina_columns.append(col)
                    else:
                        df_nominas[col] = None # Add missing columns

                df_nominas = df_nominas[final_nomina_columns] # Apply the order
                # Drop Implocal-specific columns from Nomina dataframe if they are empty.
                # This makes the Nomina sheet cleaner, asuming implocal is not relevant for Nomina..
                # df_nominas = df_nominas.drop(columns=[
                #                              col for col in implocal_cols_to_drop if col in df_nominas.columns], errors='ignore')
                df_nominas = df_nominas.drop(
                    columns=['CFDI_Type', 'ImpLocal_TrasladosLocales_Details'], errors='ignore')

                df_nominas.to_excel(
                    writer, sheet_name='Nomina', index=False)
                print(
                    f"Exported {len(nomina_data_list)} CFDI Nomina complement 1.2 to 'Nomina' sheet.")
            else:
                print("No Nomina data to export.")
        print(f"\nSuccesfully exported data to Excel: {output_file_path}")

    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        print("Please ensure 'openpyxl' is installed (pip install openpyxl) and the output path is valid.")
