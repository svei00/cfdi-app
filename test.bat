@echo off
REM ============================================================
REM  test.bat - Procesa la carpeta de prueba XML-Test SIN pedir
REM  rutas y genera test_output.xlsx en la raiz del proyecto.
REM  Doble clic para probar el pipeline rapido (sin la GUI).
REM ============================================================
setlocal
cd /d "%~dp0"

echo Procesando XML-Test...
python cli.py "%~dp0XML-Test" -o "%~dp0test_output.xlsx" --open

echo.
echo Listo. (Salida: test_output.xlsx)
pause
