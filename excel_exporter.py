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

    # Ensure output directory exists.
    output_dir = os.path.dirname(output_file_path)
    os.makedirs(output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
            if invoice_data_list:
                df_invoices = pd.DataFrame(invoice_data_list)
                # Define columns specific to Nomina that should be dropped from Invoice sheet.
                nomina_cols_to_drop = [
                    col_name for _, _, _, col_name in xml_parser.NOMINA_FIELDS_TO_EXTRACT]
                nomina_cols_to_drop.extend(
                    ['TotalGravado', 'TotalExento', 'TotalDeducciones', 'TotalOtrosPagos'])

                # Define columns specific to ImpLocal that should be dropped from Nomina sheet.
                implocal_cols_to_drop = [
                    "ImpLocal_TotalRetenciones",
                    "ImpLocal_TotalTraslados",
                    "ImpLocal_TrasladadosLocales_Details",
                ]

                # Drop nomina-specific columns from invoice dataframe.
                df_invoices = df_invoices.drop(columns=[
                                               col for col in nomina_cols_to_drop if col in df_invoices.columns], errors='ignore')
                # Drop the type column.
                df_invoices = df_invoices.drop(
                    columns=['CFDI_Type'], errors='ignore')
                df_invoices.to_excel(
                    writer, sheet_name='Invoices', index=False)
                print(
                    f"Exported {len(invoice_data_list)} regular CFDI invoices to 'Invoices' sheet.")
            else:
                print("No Invoice data to export.")

            # Nomina 1.2
            if nomina_data_list:
                df_nominas = pd.DataFrame(nomina_data_list)
                # Drop Implocal-specific columns from Nomina dataframe if they are empty.
                # This makes the Nomina sheet cleaner, asuming implocal is not relevant for Nomina..
                df_nominas = df_nominas.drop(columns=[
                                             col for col in implocal_cols_to_drop if col in df_nominas.columns], errors='ignore')
                df_nominas = df_nominas.drop(
                    columns=['CFDI_Type'], errors='ignore')
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
