**CFDI XML Processor**

**Overview**

This project provides a Python-based tool to parse
Comprobantes Fiscales Digitales por Internet (CFDI) XML files, specifically
supporting both **CFDI Version 3.3** and **CFDI Version 4.0**. It
extracts key financial and tax-related data from these XML documents and
organizes them into an Excel spreadsheet with separate sheets for
"Invoices" and "Nomina" (Payroll) complements.

The application is designed with modularity in mind to
facilitate future updates and maintenance.

**Features**

- **CFDI
   Version Detection:** Automatically identifies and parses XML files based
   on their CFDI version (3.3 or 4.0).
- **Comprehensive
   Data Extraction:** Extracts detailed information from cfdi:Comprobante, cfdi:Emisor,
   cfdi:Receptor, cfdi:Conceptos, cfdi:Impuestos, tfd:TimbreFiscalDigital
   elements.
- **Nomina
   1.2 Complement Support:** Extracts specific data from nomina12:Nomina
   complements for payroll-related CFDIs, including detailed perceptions and
   deductions.
- **Local
   Taxes (Impuestos Locales) Support:** Extracts data from implocal:ImpuestosLocales
   complement.
- **IEDU
   Complement Support:** Extracts educational institution data from iedu:instEducativas
   complement.
- **Dynamic
   Folder Selection:** Utilizes a graphical user interface (GUI) to allow
   users to select the input directory for XML files and the output directory
   for the Excel report.
- **Remember
   Last Used Directory:** Remembers the last folder selected by the user
   for convenience.
- **Automated
   Excel Export:** Exports parsed data into a well-structured Excel file
   with separate sheets for different document types.
- **Dynamic
   Filename Generation:** Generates intelligent filenames for the Excel
   report based on the RFCs and dates found in the processed XMLs (e.g., [RFC]_Emitidas_YYYY_MM.xlsx).
- **Excel
   Column Auto-sizing:** Automatically adjusts column widths in the
   generated Excel file for better readability.

**Project Structure**

The project is organized into the following files:

/YourProjectRoot/

├── AdminXML/                   # Parent directory for
application data (created by script)

│   ├──
BovedaCFDI/             # Default input
directory for XMLs (created by script)

│   └── Reports/                # Default output directory for
Excel reports (created by script)

│       └──
last_used_directory.txt # Stores the last selected directory

├── cfdi_processor_app/         # Your application's main code
directory

│   ├── main.py                 # Main entry point, handles UI
and dispatches parsing

│   ├──
constants.py            # Defines shared
XML namespaces, mapping dictionaries, and column orders

│   ├──
xml_parser_33.py        # Contains
parsing logic specific to CFDI 3.3

│   ├──
xml_parser_40.py        # Contains
parsing logic specific to CFDI 4.0

│   └──
excel_exporter.py       # Handles data
transformation to Pandas DataFrame and Excel export

└── README.md                   # This documentation file

*(Note: The AdminXML directory structure is created
relative to where main.py is run from, specifically two levels up from cfdi_processor_app/.)*

**Installation**

Before running the application, you need to have Python
installed (Python 3.7+ is recommended).

1. **Clone
  or Download the Project:** (If using Git)
2. git
  clone <your-repository-url>
3. cd
  
  <your-project-root-directory>
  

(If downloading manually, unzip the files into your desired
project root directory).

4. **Install
  Dependencies:** This project relies on pandas and openpyxl. You can
  install them using pip:
5. pip
  install pandas openpyxl

**Usage**

To run the CFDI XML Processor:

1. **Navigate
  to the cfdi_processor_app directory:**
2. cd
  /path/to/YourProjectRoot/cfdi_processor_app

*(Replace /path/to/YourProjectRoot/ with the actual path
where you've placed the project.)*

3. **Execute
  the main.py script:**
4. python
  main.py
5. **Follow
  the Prompts:**

- The
   application will first ensure the AdminXML/BovedaCFDI and AdminXML/Reports
   directories exist.
- A
   GUI window will pop up asking you to select the folder containing your
   CFDI XML files.
- After
   processing, another GUI window will appear to ask where you want to save
   the generated Excel report.

**Versioning and Development Guidelines**

This project is versioned using Git.

- The main
   branch typically holds the latest stable and released version of the
   application.
- New
   features and significant changes are developed on separate branches (e.g.,
   develop, feature/your-feature-name).
- Regular
   commits with descriptive messages are encouraged.

To contribute or manage your own development:

1. **Switch
  to the develop branch (or create one):** git checkout develop (if it
  exists) or git checkout -b develop (to create and switch)
2. **Make
  your changes.**
3. **Commit
  your changes:** git add . git commit -m "Descriptive message about
  your changes"
4. **Push
  your changes:** git push origin develop (if you're using a remote
  repository)
5. **Merge
  back to main when ready:** git checkout main git merge develop git push
  origin main

**Version History**

- **v0.1.0
  
  - Initial CFDI 4.0 Support (Conceptual)**
- Basic
   parsing for CFDI 4.0 XMLs.
  
- Excel
   export functionality.
  
- **v0.2.0
  
  - Enhanced Parsing & Modularity (Current Version)**
- Added
   support for CFDI 3.3 XML files.
  
- Implemented
   a modular project structure (constants.py, xml_parser_33.py, xml_parser_40.py).
  
- Improved
   Excel export with column auto-sizing.
  
- Enhanced
   dynamic folder selection and persistence.
  
- Prepared
   for future CFDI versions (e.g., 4.1).
  

**License**

All rights reserved