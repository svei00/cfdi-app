# CFDI Processor

Herramienta para procesar Comprobantes Fiscales Digitales por Internet (CFDI)
del SAT (México). Lee una carpeta de XMLs (y/o .zip), detecta automáticamente
la versión (CFDI 3.3 / 4.0, Nómina 1.2, Pagos 2.0), y exporta todo a un Excel
con hojas separadas por tipo de documento.

> Para el diagnóstico de bugs, las fases del proyecto y las decisiones de
> arquitectura, ver [ROADMAP.md](ROADMAP.md). Para la especificación completa
> del producto, ver [PROMPT.md](PROMPT.md).

## Instalación

Requiere Python 3.10+.

```
pip install -e .
```

Esto instala el paquete `cfdi_app` en modo editable (usa `pyproject.toml`) y
sus dependencias: `pandas`, `openpyxl`, `PySide6`.

## Uso

### Interfaz gráfica (recomendado)

Doble clic en **`run_gui.bat`** — abre la ventana sin dejar una consola negra
abierta. Si algo no arranca, usa **`run_gui_debug.bat`** (consola visible) y
revisa el registro en `Documents\CFDI-Processor\Logs\cfdi-app.log`.

Equivalente por línea de comandos:
```
pythonw -m cfdi_app     REM sin consola
python -m cfdi_app      REM con consola, para depurar
```

Flujo: seleccionar carpeta → Procesar → (al terminar) Guardar Excel… → Abrir
archivo. Se puede reprocesar cuantas veces se quiera sin reiniciar la app.

### Línea de comandos (sin diálogos)

```
python -m cfdi_app.cli <carpeta_con_xmls> [-o salida.xlsx] [--open]
```

`test.bat` usa este modo para procesar `XML-Test/` de un doble clic.

## Estructura del proyecto

```
cfdi-app/
├── pyproject.toml
├── requirements.txt
├── run_gui.bat / run_gui_debug.bat / test.bat
├── src/cfdi_app/
│   ├── __main__.py       # punto de entrada de la GUI
│   ├── paths.py          # rutas de datos (Documents/CFDI-Processor/)
│   ├── log_setup.py       # logging a archivo + captura de errores no manejados
│   ├── constants.py       # namespaces XML, catálogos SAT, orden de columnas
│   ├── core.py            # pipeline carpeta -> parseo -> Excel, sin UI
│   ├── cli.py              # front-end de consola sin diálogos
│   ├── parsers/            # UN módulo por versión CFDI (ver regla abajo)
│   │   ├── xml_parser_33.py
│   │   ├── xml_parser_40.py
│   │   └── pagos_parser_20.py
│   ├── exporters/
│   │   └── excel_exporter.py
│   └── ui/
│       ├── state.py        # máquina de estados (sin dependencia de Qt)
│       ├── worker.py        # QThread worker
│       └── main_window.py   # ventana principal PySide6
└── tests/                  # python -m unittest discover -s tests
```

**Regla de aislamiento por versión** (no se toca): cada versión de CFDI vive
en su propio módulo parser. Cuando el SAT libere una nueva versión (4.1, 5.0,
un nuevo complemento), se agrega un módulo nuevo + una rama de despacho en
`core.py` — los parsers existentes no se modifican.

## Datos de la aplicación

Por defecto, la bóveda de XMLs, los reportes y los logs viven en:

```
%USERPROFILE%\Documents\CFDI-Processor\
├── BovedaCFDI\
├── Reports\
└── Logs\cfdi-app.log
```

(Antes de F2 esto vivía en `D:\AdminXML`, nombre heredado sin querer de la
app competidora MiAdminXML — ver ROADMAP.md decisión D4.)

## Pruebas

```
python -m unittest discover -s tests
```

## Licencia

Todos los derechos reservados.
