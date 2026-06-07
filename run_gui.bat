@echo off
REM ============================================================
REM  run_gui.bat - Lanza la interfaz grafica SIN dejar una consola
REM  abierta (corrige el Bug 2 del ROADMAP.md: pythonw.exe no crea
REM  ventana de consola, y "start" desacopla el proceso del .bat).
REM  Requiere haber corrido una vez: pip install -e .
REM ============================================================
cd /d "%~dp0"
start "" pythonw -m cfdi_app
