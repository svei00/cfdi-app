# --- cfdi_processor/excel_exporter.py ---
import pandas as pd
import os
# Importar los módulos de parser para acceder a sus listas de campos para el orden de columnas.
# Asegúrate de que estos imports coincidan con los nombres de tus archivos de parser.
# Importar órdenes de columna
from constants import INVOICE_COLUMN_ORDER, PAGOS_COLUMN_ORDER
from xml_parser_33 import NOMINA_FIELDS_TO_EXTRACT as NOMINA_FIELDS_33
from xml_parser_40 import NOMINA_FIELDS_TO_EXTRACT as NOMINA_FIELDS_40


def export_to_excel(invoice_data_list, nomina_data_list, pagos_data_list, output_file_path):
    """
    Exporta listas de diccionarios (una para facturas, otra para nóminas, otra para pagos)
    a un archivo de Excel con hojas separadas usando Pandas.

    Args:
        invoice_data_list (list): Una lista de diccionarios para facturas regulares.
        nomina_data_list (list): Lista de diccionarios para el complemento de nómina.
        pagos_data_list (list): Lista de diccionarios para el complemento de pagos.
        output_file_path (str): La ruta completa donde se guardará el archivo de Excel.
    """
    if not invoice_data_list and not nomina_data_list and not pagos_data_list:
        print("No hay datos para exportar. No se creará el archivo de Excel.")
        return

    # --- LÓGICA NUEVA: Manejar letras de unidad sin subcarpeta ---
    # Verificar si output_file_path es solo una letra de unidad (ej., "D:")
    # Esto asume las convenciones de rutas de Windows (letra de unidad seguida de dos puntos)
    if os.path.ismount(output_file_path) and len(output_file_path) == 2 and output_file_path[1] == ':':
        # Si es solo una letra de unidad, añadir una subcarpeta predeterminada
        # Por ejemplo, D: se convierte en D:\CFDI_Exports
        output_file_path = os.path.join(
            output_file_path, "CFDI_Exports", "CFDI_Report.xlsx")
        print(
            f"Advertencia: La ruta de salida era una raíz de unidad. Ajustando a: {output_file_path}")
    # --- FIN LÓGICA NUEVA ---

    # Asegurarse de que el directorio de salida exista.
    # os.path.dirname obtiene la parte del directorio de la ruta
    output_dir = os.path.dirname(output_file_path)
    # Si output_file_path era solo un nombre de archivo (ej., "informe.xlsx"), output_dir está vacío
    if not output_dir:
        # Fallback a una carpeta de informes predeterminada en el directorio de trabajo actual
        output_dir = os.path.join(os.getcwd(), "CFDI_Processor_App", "Reports")

    os.makedirs(output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
            if invoice_data_list:
                df_invoices = pd.DataFrame(invoice_data_list)

                # Definir columnas específicas de Nómina que deben eliminarse de la hoja de Facturas.
                # Usar ambos conjuntos de campos de Nómina para mayor seguridad.
                nomina_cols_to_drop = [col_name for _,
                                       _, _, col_name in NOMINA_FIELDS_33]
                nomina_cols_to_drop.extend(
                    [col_name for _, _, _, col_name in NOMINA_FIELDS_40])
                nomina_cols_to_drop.extend(
                    ['TotalGravado', 'TotalExcento', 'TotalDeducciones', 'TotalOtrosPagos'])

                # Definir columnas específicas de ImpLocal que deben eliminarse de la hoja de Facturas.
                implocal_cols_to_drop = [
                    "Total Retenciones Locales",
                    "Total Traslados Locales",
                    "ImpLocal_TrasladosLocales_Details",
                ]

                # Definir columnas específicas de Pagos que deben eliminarse de la hoja de Facturas.
                # Estas son columnas que solo tienen sentido en la hoja de Pagos.
                pagos_cols_to_drop = [
                    "Version Pago", "TotalRetencionesIVA", "TotalRetencionesISR", "TotalRetencionesIEPS",
                    "TotalTrasladosBaseIVA16", "TotalTrasladosImpuestoIVA16", "TotalTrasladosBaseIVA8",
                    "TotalTrasladosImpuestoIVA8", "TotalTrasladosBaseIVA0", "TotalTrasladosImpuestoIVA0",
                    "TotalTrasladadoBaseIVAExento", "MontoTotalPagos", "FechaPago", "FormaDePagoP",
                    "MonedaP", "TipoCambioP", "Monto Pago", "NumOperacion", "RFCEmisorCtaOrd",
                    "NombreBancoOrdExt", "CtaOrdenante", "RFCEmisorCTABen", "CtaBeneficiario",
                    "TipoCadPago", "CertPago", "CadPago", "SelloPago", "IdDocumento Relacionado",
                    "Serie Relacionada", "Folio Relacionado", "MonedaDR", "TipoCambioDR",
                    "EquivalenciaDR", "MetodoDePagoDR", "NumParcialidad", "ImpSaldoAnt",
                    "ImpPagado", "ImpSaldoInsoluto", "ObjetoImpDR", "IVA Excento", "IVA Excento Base",
                    "IVA Cero", "IVA Cero Base", "IVA 8 Base", "IVA 8 Importe", "IVA 16 Base",
                    "IVA 16 Importe", "IEPS Cero", "IEPS Cero Base", "IEPS 3 Base", "IEPS 3 Importe",
                    "IEPS 6 Base", "IEPS 6 Importe", "IEPS 7 Base", "IEPS 7 Importe", "IEPS 8 Base",
                    "IEPS 8 Importe", "IEPS 9 Base", "IEPS 9 Importe", "IEPS 25 Base", "IEPS 25 Importe",
                    "IEPS 26.5 Base", "IEPS 26.5 Importe", "IEPS 30 Base", "IEPS 30 Importe",
                    "IEPS 30.4 Base", "IEPS 30.4 Importe", "IEPS 50 Base", "IEPS 50 Importe",
                    "IEPS 53 Base", "IEPS 53 Importe", "IEPS 160 Base", "IEPS 160 Importe",
                    "Ret ISR 1.25 Base", "Ret ISR 1.25 Importe", "Ret ISR 10 Base", "Ret ISR 10 Importe",
                    "Ret IVA 4 Base", "Ret IVA 4 Importe", "Ret IVA 10.667 Base", "Ret IVA 10.667 Importe",
                    "Ret IVA 2 Base", "Ret IVA 2 Importe", "Ret IVA 5.33 Base", "Ret IVA 5.33 Importe",
                    "Ret IVA 8 Base", "Ret IVA 8 Importe", "Ret IVA 6 Base", "Ret IVA 6 Importe",
                    "Ret IVA 16 Base", "Ret IVA 16 Importe",
                    # También las columnas de RFC/Nombre/Regimen/Domicilio que son específicas de Pagos
                    "RFC Emisor CFDI", "Nombre Emisor CFDI", "Regimen Fiscal Emisor CFDI",
                    "Lugar de Expedicion CFDI", "RFC Receptor CFDI", "Nombre Receptor CFDI",
                    "Regimen Fiscal Receptor CFDI", "DomicilioFiscalReceptor CFDI",
                    "ResidenciaFiscal CFDI", "NumRegIdTrib CFDI", "UsoCFDI CFDI",
                    "Version CFDI", "TipoComprobante", "Serie CFDI", "Folio CFDI", "UUID CFDI",
                    "No. Certificado Emisor", "No. Certificado SAT"
                ]

                # Combinar todas las columnas a eliminar de la hoja de Facturas
                all_cols_to_drop_from_invoices = list(
                    set(nomina_cols_to_drop + implocal_cols_to_drop + pagos_cols_to_drop))

                # Eliminar las columnas específicas de nómina, implocal y pagos del dataframe de facturas.
                df_invoices = df_invoices.drop(columns=[
                                               col for col in all_cols_to_drop_from_invoices if col in df_invoices.columns], errors='ignore')

                # Reordenar las columnas de facturas según INVOICE_COLUMN_ORDER
                df_invoices = df_invoices[INVOICE_COLUMN_ORDER].copy()

                # Eliminar la columna de tipo interno.
                df_invoices = df_invoices.drop(
                    columns=['CFDI_Type'], errors='ignore')
                df_invoices.to_excel(
                    writer, sheet_name='Invoices', index=False)
                print(
                    f"Exportadas {len(invoice_data_list)} facturas CFDI regulares a la hoja 'Invoices'.")
            else:
                print("No hay datos de Facturas para exportar.")

            # Nomina 1.2
            if nomina_data_list:
                df_nominas = pd.DataFrame(nomina_data_list)
                # Eliminar columnas específicas de ImpLocal y Pagos del dataframe de Nómina si están presentes.
                # Esto hace que la hoja de Nómina sea más limpia.
                implocal_and_pagos_cols_to_drop = list(
                    set(implocal_cols_to_drop + pagos_cols_to_drop))
                df_nominas = df_nominas.drop(columns=[
                    col for col in implocal_and_pagos_cols_to_drop if col in df_nominas.columns], errors='ignore')
                df_nominas = df_nominas.drop(
                    columns=['CFDI_Type'], errors='ignore')
                df_nominas.to_excel(
                    writer, sheet_name='Nomina', index=False)
                print(
                    f"Exportados {len(nomina_data_list)} complementos de Nómina CFDI 1.2 a la hoja 'Nomina'.")
            else:
                print("No hay datos de Nómina para exportar.")

            # Pagos 2.0
            if pagos_data_list:
                df_pagos = pd.DataFrame(pagos_data_list)
                # Eliminar columnas específicas de Facturas y Nómina del dataframe de Pagos si están presentes.
                invoice_and_nomina_cols_to_drop = list(
                    set(INVOICE_COLUMN_ORDER + nomina_cols_to_drop))
                df_pagos = df_pagos.drop(columns=[
                    col for col in invoice_and_nomina_cols_to_drop if col in df_pagos.columns], errors='ignore')

                # Reordenar las columnas de pagos según PAGOS_COLUMN_ORDER
                df_pagos = df_pagos[PAGOS_COLUMN_ORDER].copy()

                df_pagos = df_pagos.drop(
                    columns=['CFDI_Type'], errors='ignore')
                df_pagos.to_excel(
                    writer, sheet_name='Pagos', index=False)
                print(
                    f"Exportados {len(pagos_data_list)} complementos de Pagos CFDI 2.0 a la hoja 'Pagos'.")
            else:
                print("No hay datos de Pagos para exportar.")

        print(f"\nDatos exportados exitosamente a Excel: {output_file_path}")

    except Exception as e:
        print(f"Error al exportar a Excel: {e}")
        print("Por favor, asegúrate de que 'openpyxl' esté instalado (pip install openpyxl) y la ruta de salida sea válida.")
