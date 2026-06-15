# --- cfdi_app/exporters/excel_exporter.py ---
import logging
import os

import pandas as pd
from openpyxl.utils import get_column_letter

from cfdi_app.constants import (
    INVOICE_COLUMN_ORDER, PAGOS_COLUMN_ORDER, INTERNAL_ONLY_FIELDS,
)

logger = logging.getLogger(__name__)


def autosize_columns(worksheet, dataframe):
    """Ajusta el ancho de cada columna de `worksheet` al contenido de `dataframe`.

    Antes este bucle estaba repetido 3 veces (una por hoja); ahora es un solo
    helper reutilizado por Invoices/Nomina/Pagos.
    """
    for i, col in enumerate(dataframe.columns):
        max_length = len(str(col))  # encabezado
        for cell_col in worksheet.iter_cols(min_col=i + 1, max_col=i + 1, min_row=1):
            for cell in cell_col:
                if cell.value is None:
                    continue
                cell_value_str = str(cell.value)
                if isinstance(cell.value, (float, int)):
                    cell_value_str = f"{cell.value:.2f}"
                max_length = max(max_length, len(cell_value_str))
        worksheet.column_dimensions[get_column_letter(i + 1)].width = max_length + 2


def export_to_excel(invoice_data_list, nomina_data_list, pagos_data_list, output_file_path):
    """
    Exporta listas de diccionarios (una para facturas, otra para nóminas, otra para pagos)
    a un archivo de Excel con hojas separadas usando Pandas.

    Args:
        invoice_data_list (list): Una lista de diccionarios para facturas regulares.
        nomina_data_list (list): Lista de diccionarios para el complemento de nómina.
        pagos_data_list (list): Lista de diccionarios para el complemento de pagos.
        output_file_path (str): La ruta completa donde se guardará el archivo de Excel.

    Nota (ROADMAP.md §6.6): esta función YA NO atrapa excepciones internamente.
    Si el archivo destino está abierto en Excel (PermissionError) o cualquier
    otro error de escritura ocurre, la excepción SE PROPAGA para que la capa de
    UI/CLI decida cómo mostrarla (antes se tragaba en silencio y se reportaba
    éxito falso).
    """
    if not invoice_data_list and not nomina_data_list and not pagos_data_list:
        logger.info("No hay datos para exportar. No se creará el archivo de Excel.")
        return

    # Asegurarse de que el directorio de salida exista.
    output_dir = os.path.dirname(output_file_path)
    if not output_dir:
        # Fallback a una carpeta de informes predeterminada en el directorio de trabajo actual
        output_dir = os.path.join(os.getcwd(), "CFDI_Processor_App", "Reports")
    os.makedirs(output_dir, exist_ok=True)

    with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
        # --- Hoja de Invoices ---
        if invoice_data_list:
            df_invoices = pd.DataFrame(invoice_data_list)
            final_invoice_columns = [
                col for col in INVOICE_COLUMN_ORDER if col != "CFDI_Type"]
            df_invoices = df_invoices.reindex(columns=final_invoice_columns)
            df_invoices.to_excel(writer, sheet_name='Invoices', index=False)
            autosize_columns(writer.sheets['Invoices'], df_invoices)
            logger.info(
                "Exportadas %d facturas CFDI regulares a la hoja 'Invoices'.",
                len(invoice_data_list))
        else:
            logger.info("No hay datos de Facturas para exportar.")

        # --- Hoja de Nomina ---
        if nomina_data_list:
            df_nominas = pd.DataFrame(nomina_data_list)
            # Nomina no tiene una lista fija de columnas (deuda tecnica
            # conocida) - a diferencia de Invoices/Pagos, aqui SI hay que
            # excluir a mano los campos internos de F2.6 (D25), o saldrian
            # como texto de lista de Python en una celda.
            df_nominas = df_nominas.drop(
                columns=['CFDI_Type'] + INTERNAL_ONLY_FIELDS, errors='ignore')
            df_nominas.to_excel(writer, sheet_name='Nomina', index=False)
            autosize_columns(writer.sheets['Nomina'], df_nominas)
            logger.info(
                "Exportados %d complementos de Nómina CFDI 1.2 a la hoja 'Nomina'.",
                len(nomina_data_list))
        else:
            logger.info("No hay datos de Nómina para exportar.")

        # --- Hoja de Pagos ---
        if pagos_data_list:
            df_pagos = pd.DataFrame(pagos_data_list)
            final_pagos_columns = [
                col for col in PAGOS_COLUMN_ORDER if col != "CFDI_Type"]
            df_pagos = df_pagos.reindex(columns=final_pagos_columns)
            df_pagos.to_excel(writer, sheet_name='Pagos', index=False)
            autosize_columns(writer.sheets['Pagos'], df_pagos)
            logger.info(
                "Exportados %d complementos de Pagos CFDI 2.0 a la hoja 'Pagos'.",
                len(pagos_data_list))
        else:
            logger.info("No hay datos de Pagos para exportar.")

    logger.info("Datos exportados exitosamente a Excel: %s", output_file_path)
