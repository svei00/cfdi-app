# --- cfdi_processor/excel_exporter.py ---
import pandas as pd
import os
from openpyxl.utils import get_column_letter  # Import for column auto-sizing
# Import constants directly, as files are in the same directory or treated as siblings.
from constants import INVOICE_COLUMN_ORDER, NOMINA_FIELDS_TO_EXTRACT


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

    # Ensure output directory exists.
    output_dir = os.path.dirname(output_file_path)
    os.makedirs(output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
            if invoice_data_list:
                df_invoices = pd.DataFrame(invoice_data_list)

                # Reorder columns according to INVOICE_COLUMN_ORDER from constants.py
                # Add any missing columns to the DataFrame to match the order
                for col in INVOICE_COLUMN_ORDER:
                    if col not in df_invoices.columns:
                        # Add missing columns as None (which becomes NaN in Pandas)
                        df_invoices[col] = None
                df_invoices = df_invoices[INVOICE_COLUMN_ORDER]  # Reorder

                # Define columns specific to Nomina that should be dropped from Invoice sheet.
                nomina_cols_to_drop = [
                    col_name for _, _, _, col_name in NOMINA_FIELDS_TO_EXTRACT if col_name not in ["TotalGravado", "TotalExcento", "TotalDeducciones", "TotalOtrosPagos"]]
                nomina_cols_to_drop.extend(['TotalGravado', 'TotalExcento', 'TotalDeducciones', 'TotalOtrosPagos',
                                            'Version Nomina', 'Tipo Nomina', 'Fecha Pago', 'Fecha Inicial Pago',
                                            'Fecha Final Pago', 'Registro Patronal', 'CURP Patron', 'RFC Patron',
                                            'CURP', 'NSS', 'Inicio Relacion Laboral', 'Antiguedad', 'Periodicidad Pago',
                                            'SBC', 'SDI', 'Entidad', 'Total Sueldos', 'ImpuestosRetenidos'])

                # Define columns specific to ImpLocal that should be dropped from Invoice sheet if not applicable
                implocal_cols_to_drop_from_invoices = [
                    "ImpLocal_TrasladosLocales_Details",
                ]

                # Drop Nomina and specific ImpLocal related columns from invoice dataframe.
                df_invoices = df_invoices.drop(columns=[
                                               col for col in nomina_cols_to_drop if col in df_invoices.columns], errors='ignore')
                df_invoices = df_invoices.drop(columns=[
                                               col for col in implocal_cols_to_drop_from_invoices if col in df_invoices.columns], errors='ignore')

                # Drop the internal 'CFDI_Type' and 'Conceptos_Importe_Sum' columns as they are not for output
                df_invoices = df_invoices.drop(
                    columns=['CFDI_Type', 'Conceptos_Importe_Sum'], errors='ignore')

                df_invoices.to_excel(
                    writer, sheet_name='Invoices', index=False)

                # --- Auto-adjust column widths for Invoices sheet ---
                worksheet = writer.sheets['Invoices']
                for i, col in enumerate(df_invoices.columns):
                    max_length = 0
                    # Account for header length
                    max_length = max(max_length, len(str(col)))
                    # Iterate through column to find max length of cell content
                    for cell in worksheet.iter_cols(min_col=i+1, max_col=i+1, min_row=1):
                        for c in cell:
                            try:
                                if len(str(c.value)) > max_length:
                                    max_length = len(str(c.value))
                            except TypeError:
                                pass  # Handle cases where cell value is None or non-string
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[get_column_letter(
                        i + 1)].width = adjusted_width
                # --- End auto-adjust ---

                print(
                    f"Exported {len(invoice_data_list)} CFDI Invoices to 'Invoices' sheet.")
            else:
                print("No Invoice data to export.")

            # Nomina Data
            if nomina_data_list:
                df_nominas = pd.DataFrame(nomina_data_list)

                # Drop CFDI Invoice specific columns from Nomina sheet
                invoice_only_cols_to_drop = [
                    "Tipo", "SubTotal", "Descuento", "Total IEPS", "IVA 16%", "Retenido IVA", "Retenido ISR",
                    "ISH", "Total", "Total Trasladados", "Total Retenidos", "Total LocalTrasladado",
                    "Total LocalRetenido", "Tipo De Cambio", "FormaDePago", "Metodo de Pago", "NumCtaPago",
                    "Condicion de Pago", "Conceptos", "Combustible", "IEPS 3%", "IEPS 6%", "IEPS 7%", "IEPS 8%",
                    "IEPS 9%", "IEPS 26.5%", "IEPS 30%", "IEPS 30.4%", "IEPS 53%", "IEPS 160%", "IVA 8%", "IVA Ret 6%",
                    "UUID Relacion", "TipoDeRelacion", "ResidenciaFiscal", "NumRegIdTrib", "DomicilioFiscalReceptor",
                    "Exportacion",
                    "Verificado ó Asoc.", "Estado SAT", "EstadoPago",
                    "Direccion Emisor", "Localidad Emisor", "Direccion Receptor", "Localidad Receptor",
                    "UsoCFDI", "RegimenFiscalReceptor"
                ]

                # Drop the internal 'CFDI_Type' and 'Conceptos_Importe_Sum' columns
                df_nominas = df_nominas.drop(columns=[
                    col for col in invoice_only_cols_to_drop if col in df_nominas.columns], errors='ignore')
                df_nominas = df_nominas.drop(columns=[
                    'CFDI_Type', 'Conceptos_Importe_Sum', "ImpLocal_TrasladosLocales_Details"], errors='ignore')

                df_nominas.to_excel(writer, sheet_name='Nomina', index=False)

                # --- Auto-adjust column widths for Nomina sheet ---
                worksheet = writer.sheets['Nomina']
                for i, col in enumerate(df_nominas.columns):
                    max_length = 0
                    # Account for header length
                    max_length = max(max_length, len(str(col)))
                    # Iterate through column to find max length of cell content
                    for cell in worksheet.iter_cols(min_col=i+1, max_col=i+1, min_row=1):
                        for c in cell:
                            try:
                                if len(str(c.value)) > max_length:
                                    max_length = len(str(c.value))
                            except TypeError:
                                pass  # Handle cases where cell value is None or non-string
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[get_column_letter(
                        i + 1)].width = adjusted_width
                # --- End auto-adjust ---

                print(
                    f"Exported {len(nomina_data_list)} CFDI Nomina complements to 'Nomina' sheet.")
            else:
                print("No Nomina data to export.")
        print(f"\nSuccessfully exported data to Excel: {output_file_path}")

    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        print("Please ensure 'openpyxl' is installed (pip install openpyxl) and the output path is valid.")
