# --- main.py ---
# Front-end de CONSOLA / Tkinter (modo de respaldo).
#
# La GUI principal ahora vive en gui.py (PySide6). Este archivo se conserva como
# flujo alterno y para uso por linea de comandos. TODA la logica de procesamiento
# vive en core.py; aqui solo hay dialogos de Tkinter y mensajes de consola.
import platform
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import core


def clear_terminal():
    """Limpia la pantalla de la terminal segun el sistema operativo."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def select_xml_directory_gui(title_text="Seleccionar Carpeta de XMLs"):
    """
    Dialogo Tkinter para seleccionar el directorio de XMLs.
    Recuerda el ultimo directorio usado, o por defecto usa BOVEDA_XML_DIR.
    """
    initial_dir_to_use = core.read_last_used_directory() or core.BOVEDA_XML_DIR

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()

    messagebox.showinfo(
        "Seleccion de Carpeta",
        "A continuacion aparecera una ventana de seleccion de carpeta. "
        "Por favor, selecciona el directorio que contiene tus archivos XML."
    )

    selected_directory = filedialog.askdirectory(
        initialdir=initial_dir_to_use,
        title=title_text
    )

    root.destroy()

    if selected_directory:
        core.save_last_used_directory(selected_directory)

    return selected_directory


def select_file_save_path_gui(initial_dir=".", default_filename="CFDI_Export.xlsx",
                              title_text="Guardar Informe de Excel Como"):
    """Dialogo Tkinter para elegir donde guardar el archivo de Excel."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()

    messagebox.showinfo(
        "Guardar Ubicacion del Archivo",
        "A continuacion aparecera una ventana para guardar archivos. "
        "Por favor, selecciona donde guardar tu informe de Excel.\n"
        f"Nombre de archivo sugerido: {default_filename}"
    )

    file_path = filedialog.asksaveasfilename(
        initialdir=initial_dir,
        initialfile=default_filename,
        title=title_text,
        defaultextension=".xlsx",
        filetypes=[("Archivos de Excel", "*.xlsx"),
                   ("Todos los archivos", "*.*")]
    )

    root.destroy()
    return file_path


def main():
    """Flujo principal de consola para procesar CFDIs."""
    clear_terminal()

    print("------ Aplicacion de Procesamiento de Facturas CFDI (modo consola) ------")
    print("Analiza las facturas electronicas XML de un directorio y exporta los datos a Excel.")
    print("Detecta automaticamente CFDI regular, Complemento de Nomina o Complemento de Pagos.")
    print("Sugerencia: la interfaz grafica esta disponible ejecutando 'python gui.py'.")
    print("--------------------------------------------------\n")

    core.create_initial_directories()

    input_folder = select_xml_directory_gui(
        title_text="Seleccionar Carpeta de XMLs CFDI")
    if not input_folder:
        print("No se selecciono ninguna carpeta. Saliendo.")
        return

    if not os.path.isdir(input_folder):
        print(f"Error: La ruta '{input_folder}' no es un directorio valido.")
        return

    print(f"\nEscaneando directorio: {input_folder}")
    result = core.process_path(input_folder, on_log=print)

    if not result.has_data:
        print("No se procesaron archivos XML CFDI validos. "
              "Verifica el directorio y los formatos de archivo.")
        return

    print(f"\nSe procesaron {result.processed_count} archivos XML. "
          f"({result.error_count} errores encontrados.)")
    print(f"Se encontraron {len(result.invoice_data)} Facturas Electronicas CFDI.")
    print(f"Se encontraron {len(result.nomina_data)} Complementos de Nomina CFDI 1.2.")
    print(f"Se encontraron {len(result.pagos_data)} Complementos de Pagos CFDI 2.0.\n")

    default_name = core.build_default_filename(result.all_parsed_data)
    excel_output_path = select_file_save_path_gui(
        initial_dir=core.REPORTS_DIR,
        default_filename=default_name,
        title_text="Guardar Informe de Excel CFDI"
    )

    if not excel_output_path:
        print("No se selecciono ninguna ruta de salida. Saliendo.")
        return

    core.export_report(result, excel_output_path)

    print("\nProcesamiento completado.")
    print(f"Salida guardada en: {excel_output_path}")

    if messagebox.askyesno("Proceso Completado", "Deseas abrir el reporte de Excel ahora?"):
        core.open_file(excel_output_path)


if __name__ == "__main__":
    main()
