# --- cfdi_app/exporters/csv_exporter.py ---
"""Exportacion CSV de UNA tabla (F2.9, ROADMAP.md Sec.18/D43-D45).

Sin Qt, sin pandas: solo el modulo csv de la stdlib. Sabe escribir filas de
dicts a columnas dadas - nada mas. No conoce el visor, el filtro, ni de
donde vienen las columnas; eso es responsabilidad de core.export_tab_csv y
de ResultsView.active_tab_export_data() (capas de arriba).
"""
import csv
import logging
import os

logger = logging.getLogger(__name__)


def export_rows_to_csv(rows, columns, output_file_path):
    """Escribe `rows` (lista de dicts) a un CSV con exactamente `columns` en
    ese orden. Formato decidido en D45:
      - coma como delimitador, quoting via csv.DictWriter (los conceptos
        CFDI SI traen comas - nunca concatenar a mano).
      - utf-8-sig (BOM): evita que Excel en Windows destroce acentos/enie
        al abrir de doble clic; el BOM cuesta ~1 token, irrelevante.
      - fin de linea LF explicito (el default del modulo csv es CRLF).

    No atrapa excepciones (mismo criterio que excel_exporter, ROADMAP Sec.6.6):
    si el archivo destino esta abierto en otro programa, la excepcion se
    propaga para que la capa de UI decida como mostrarla.
    """
    output_dir = os.path.dirname(output_file_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col) for col in columns})

    logger.info(
        "CSV exportado: %s (%d filas, %d columnas)",
        output_file_path, len(rows), len(columns))
