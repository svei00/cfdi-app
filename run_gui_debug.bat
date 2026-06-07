@echo off
REM ============================================================
REM  run_gui_debug.bat - Lanza la GUI CON consola visible, para ver
REM  errores de arranque. Usa esto si run_gui.bat no abre ninguna
REM  ventana (revisa tambien Documents\CFDI-Processor\Logs\cfdi-app.log).
REM ============================================================
cd /d "%~dp0"
python -m cfdi_app
pause
