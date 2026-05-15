# --- cli.py ---
# Modo linea de comandos SIN dialogos: procesa una carpeta y exporta a Excel.
# Pensado para pruebas rapidas (ver test.bat) sin tener que elegir la ruta cada vez.
#
# Uso:
#   python cli.py <carpeta_entrada> [-o salida.xlsx] [--open]
#
# Si no se indica -o, el nombre se genera automaticamente en la carpeta Reports.
import os
import sys
import argparse

import core


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Procesa CFDIs de una carpeta y exporta a Excel (sin dialogos).")
    parser.add_argument("input_folder",
                        help="Carpeta con archivos XML y/o .zip")
    parser.add_argument("-o", "--output",
                        help="Ruta del Excel de salida (.xlsx). "
                             "Por defecto: Reports/<nombre automatico>.")
    parser.add_argument("--open", action="store_true", dest="open_after",
                        help="Abrir el Excel al terminar.")
    args = parser.parse_args(argv)

    core.create_initial_directories()

    if not os.path.isdir(args.input_folder):
        print(f"Error: no es una carpeta valida: {args.input_folder}")
        return 1

    print(f"Escaneando: {args.input_folder}")
    result = core.process_path(args.input_folder, on_log=print)

    if not result.has_data:
        print("No se procesaron archivos XML CFDI validos.")
        return 2

    output_path = args.output or os.path.join(
        core.REPORTS_DIR, core.build_default_filename(result.all_parsed_data))
    core.export_report(result, output_path)

    print(f"\nProcesados: {result.processed_count}  |  Errores: {result.error_count}")
    print(f"Facturas: {len(result.invoice_data)}  |  "
          f"Nomina: {len(result.nomina_data)}  |  "
          f"Pagos: {len(result.pagos_data)}")
    print(f"Excel guardado en: {output_path}")

    if args.open_after:
        core.open_file(output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
