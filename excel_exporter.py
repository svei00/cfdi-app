# --- cfdi_processor/excel_exporter.py ---
# This file handles exporting the parsed data to an Excel file with separate sheets.
import pandas as pd
import os
import openpyxl  # Import openpyxl to enable auto-sizing columns
# Import get_column_letter for auto-sizing columns
from openpyxl.utils import get_column_letter
# Import the xml_parser to access its field list for column order.
import xml_parser


def export_to_excel(invoice_data_list, nomina_data_list, output_file_path):
    """
    Export list of dictionaries (one for invoices, one for nominas) to an Excel file
    with separate sheets using Pandas.

    Args:
        invoice_data_list (list): A list of dictionaries for regular invoices.
        nomina_data_list (list): List of dictionaries for nomina complement.
        output_file_path (str): The full path where the Excel file will be saved.
    """
    if not invoice_data_list and not nomina_data_list:
        print("No data to export. Excel file will not be created.")
        return

    # Handle cases where output_file_path is just a drive letter (e.g., "D:")
    if os.path.ismount(output_file_path) and len(output_file_path) == 2 and output_file_path[1] == ':':
        # Removed leading '\' as os.path.join handles separators correctly
        output_file_path = os.path.join(
            output_file_path, 'CFDI_Exports', 'CFDI_Report.xlsx')
        print(
            f"Warning: Output path was a drive root. Adjusting to: {output_file_path}")

    # Ensure output directory exists.
    output_dir = os.path.dirname(output_file_path)
    if not output_dir:
        output_dir = os.path.join(os.getcwd(), 'CFDI_Processor_App', "Reports")
    os.makedirs(output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
            # Process Invoices
            if invoice_data_list:
                df_invoices = pd.DataFrame(invoice_data_list)

                # Filter columns to only include those specified in INVOICE_COLUMN_ORDER
                # and ensure they are in the correct order.
                final_invoice_columns = []
                for col in xml_parser.INVOICE_COLUMN_ORDER:
                    if col in df_invoices.columns:
                        final_invoice_columns.append(col)
                    else:
                        # Add missing columns with None to ensure all desired columns are present
                        df_invoices[col] = None

                # Apply the order
                df_invoices = df_invoices[final_invoice_columns]

                # Drop internal columns or those not needed in the final output
                df_invoices = df_invoices.drop(
                    columns=['CFDI_Type', 'ImpLocal_TrasladosLocales_Details'], errors='ignore')

                # Convert relevant numerical columns to actual numeric types for Excel
                # Using .apply(pd.to_numeric, errors='coerce') will convert to numbers and turn errors into NaN
                numeric_cols_invoice = [
                    "SubTotal", "Descuento", "Total IEPS", "IVA 16%", "Retenido IVA", "Retenido ISR", "ISH", "Total",
                    "Total Trasladados", "Total Retenidos", "Total LocalTrasladado", "Total LocalRetenido",
                    "IEPS 3%", "IEPS 6%", "IEPS 7%", "IEPS 8%", "IEPS 9%", "IEPS 26.5%", "IEPS 30%",
                    "IEPS 53%", "IEPS 160%", "IVA 8%", "IEPS 30.4%", "IVA Ret 6%"
                ]
                for col in numeric_cols_invoice:
                    if col in df_invoices.columns:
                        df_invoices[col] = pd.to_numeric(
                            df_invoices[col], errors='coerce')

                # Only write sheet if DataFrame is not empty
                if not df_invoices.empty:
                    df_invoices.to_excel(
                        writer, sheet_name='Invoices', index=False)
                    print(
                        f"Exported {len(invoice_data_list)} regular CFDI invoices to 'Invoices' sheet.")

                    # Auto-adjust column width for Invoices sheet
                    worksheet = writer.sheets['Invoices']
                    for column in worksheet.columns:
                        max_length = 0
                        column_name = column[0].value
                        if column_name:  # Check if column has a header
                            max_length = len(str(column_name))
                        for cell in column:
                            try:
                                if cell.value is not None:
                                    # Convert to string to get length, especially for numbers
                                    cell_length = len(str(cell.value))
                                    if cell_length > max_length:
                                        max_length = cell_length
                            except:
                                pass  # Ignore errors for non-string/non-numeric types
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[get_column_letter(
                            column[0].column)].width = adjusted_width
                else:
                    print(
                        "No data remaining for 'Invoices' sheet after processing and column selection.")
            else:
                print("No Invoice data to export.")

            # Process Nomina
            if nomina_data_list:
                df_nominas = pd.DataFrame(nomina_data_list)

                # Define columns to KEEP for the Nomina sheet.
                nomina_output_columns = [
                    "Fecha Emision",    # Added as the first column for Nomina sheet
                    "Fecha Timbrado",   # Added as second column for Nomina sheet
                    "Factura", "UUID", "UUID Relacion",  # Added UUID Relacion to Nomina sheet
                    "RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor",
                    "Total", "Moneda", "Tipo De Cambio", "Condicion de Pago", "FormaDePago", "Metodo de Pago",
                    "Version Nomina", "Tipo Nomina", "Fecha Pago", "Fecha Inicial Pago", "Fecha Final Pago",
                    "Total Sueldos", "Total Deducciones", "Total Otros Pagos", "Registro Patronal",
                    "CURP Patron", "RFC Patron", "CURP", "NSS", "Inicio Relacion Laboral", "Antiguedad",
                    "Periodicidad Pago", "SBC", "SDI", "Entidad", "TotalGravado", "TotalExcento",
                    "ImpuestosRetenidos", "Archivo XML", "Complemento"
                ]

                # Ensure all desired columns are present, fill with None if missing
                final_nomina_columns = []
                for col in nomina_output_columns:
                    if col in df_nominas.columns:
                        final_nomina_columns.append(col)
                    else:
                        df_nominas[col] = None

                # Apply the order
                df_nominas = df_nominas[final_nomina_columns]

                # Drop internal columns or those not needed in the final output
                df_nominas = df_nominas.drop(
                    columns=['CFDI_Type', 'ImpLocal_TrasladosLocales_Details'], errors='ignore')

                # Convert relevant numerical columns to actual numeric types for Excel
                numeric_cols_nomina = [
                    "Total", "Total Sueldos", "Total Deducciones", "Total Otros Pagos",
                    "SBC", "SDI", "ImpuestosRetenidos", "TotalGravado", "TotalExcento"
                ]
                for col in numeric_cols_nomina:
                    if col in df_nominas.columns:
                        df_nominas[col] = pd.to_numeric(
                            df_nominas[col], errors='coerce')

                # Only write sheet if DataFrame is not empty
                if not df_nominas.empty:
                    df_nominas.to_excel(
                        writer, sheet_name='Nomina', index=False)
                    print(
                        f"Exported {len(nomina_data_list)} CFDI Nomina complement 1.2 to 'Nomina' sheet.")

                    # Auto-adjust column width for Nomina sheet
                    worksheet = writer.sheets['Nomina']
                    for column in worksheet.columns:
                        max_length = 0
                        column_name = column[0].value
                        if column_name:
                            max_length = len(str(column_name))
                        for cell in column:
                            try:
                                if cell.value is not None:
                                    cell_length = len(str(cell.value))
                                    if cell_length > max_length:
                                        max_length = cell_length
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[get_column_letter(
                            column[0].column)].width = adjusted_width
                else:
                    print(
                        "No data remaining for 'Nomina' sheet after processing and column selection.")
            else:
                print("No Nomina data to export.")
        print(f"\nSuccessfully exported data to Excel: {output_file_path}")

    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        print("Please ensure 'openpyxl' is installed (pip install openpyxl) and the output path is valid.")
