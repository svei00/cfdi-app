# --- cfdi_app/reports/ ---
"""Capa de reportes fiscales (Papel de Trabajo, F2.8 / ROADMAP §17).

Logica PURA: sin Qt, sin openpyxl, sin disco. Toma las listas de dicts que
ya produce el pipeline (core.ProcessResult) y devuelve estructuras de datos
(filas de detalle, filas de resumen mensual). El armado del Excel vive en
exporters/pt_exporter.py y solo CONSUME lo que aqui se calcula.

Regla anti-alucinacion EXTENDIDA a lo fiscal (ROADMAP §13.1/§17): cada
clasificacion tiene su fundamento legal citado en el codigo (y en la hoja
Fundamentos). Ningun criterio fiscal se inventa.
"""
