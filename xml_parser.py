# --- cfdi_processor/xml_parser.py ---
# ----------XML Processor----------
# source: http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd
import xml.etree.ElementTree as ET
import os

"""
Define the XML namespaces used in CFDI 4.0 for parsing.
This is crucial for correctly interpreting the XML structure
and finding the necessary elements.
"""
NAMESPACES = {
    'cfdi': 'http://www.sat.gob.mx/cfd/4',
    'nomina12': 'http://www.sat.gob.mx/nomina12',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
    'iedu': 'http://www.sat.gob.mx/iedu',
    'implocal': 'http://www.sat.gob.mx/implocal',  # Local Taxes complement like ISH
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# Define the precise order of columns for the Invoice sheet.
# This list will be used to ensure the DataFrame columns match this order when exporting to Excel.
INVOICE_COLUMN_ORDER = [
    # Placeholder: Requires external logic/data (e.g., SAT validation, internal database).
    "Verificado ó Asoc.",
    # Placeholder: Requires external logic/data (e.g., SAT validation for 'Cancelado' status).
    "Estado SAT",
    "Version",
    "Tipo",
    "Fecha Emision",
    "Fecha Timbrado",
    # Placeholder: Not directly in XML, typically derived from payment status.
    "EstadoPago",
    # Placeholder: Not directly in XML for general invoices, present in Nomina.
    "FechaPago",
    "Factura",            # Merged field: Serie + Folio
    "UUID",
    "UUID Relacion",      # Corrected from UUID Relacionados to UUID Relacion
    "RFC Emisor",
    "Nombre Emisor",
    "LugarDeExpedicion",
    "RFC Receptor",
    "Nombre Receptor",
    "ResidenciaFiscal",
    "NumRegIdTrib",
    "UsoCFDI",
    "SubTotal",
    "Descuento",
    "Total IEPS",
    "IVA 16%",
    "Retenido IVA",
    "Retenido ISR",
    "ISH",
    "Total",
    # "TotalOriginal",      # REMOVED: Redundant as SubTotal and Total cover these aspects.
    "Total Trasladados",
    "Total Retenidos",
    "Total LocalTrasladado",
    "Total LocalRetenido",
    "Complemento",
    "Moneda",
    "Tipo De Cambio",
    "FormaDePago",
    "Metodo de Pago",
    "NumCtaPago",
    "Condicion de Pago",
    "Conceptos",          # Corrected from Descripcion to Conceptos
    # Placeholder: Not typically found in standard CFDI XML.
    "Combustible",
    "IEPS 3%",
    "IEPS 6%",
    "IEPS 7%",
    "IEPS 8%",
    "IEPS 9%",
    "IEPS 26.5%",
    "IEPS 30%",
    "IEPS 53%",
    "IEPS 160%",
    "Archivo XML",
    # Placeholder: Full address details not consistently in XML attributes.
    "Direccion Emisor",
    # Placeholder: Full address details not consistently in XML attributes.
    "Localidad Emisor",
    # Placeholder: Full address details not consistently in XML attributes.
    "Direccion Receptor",
    # Placeholder: Full address details not consistently in XML attributes.
    "Localidad Receptor",
    "IVA 8%",
    "IEPS 30.4%",
    "IVA Ret 6%",
    "RegimenFiscalReceptor",
    "DomicilioFiscalReceptor",  # Postal code.
    "CURP Dependiente",        # For IEDU Complement.
    "Nivel Educativo",    # For IEDU Complement.
    "Nombre Dependiente",      # For IEDU Complement.
]

# List of XML tags/attributes to extract for regular CFDI XML.
# Each item is a tuple: (XPath, attribute_name_if_any, default_value_if_not_found, output_column_name)
# For attributes, the XPath should point to the element containing the attribute and attribute_name_if_any should be the attribute name.
# For element text, attribute_name_if_any should be "".
# The output_column_name is how it will appear in the Excel file.
CFDI_FIELDS_TO_EXTRACT = [
    # CFDI 4.0 Invoice fields (Attributes)
    (".//cfdi:Comprobante", "Version", "4.0", "Version"),
    (".//cfdi:Comprobante", "TipoDeComprobante", "", "Tipo"),
    # Corrected output column name
    (".//cfdi:Comprobante", "Fecha", "", "Fecha Emision"),
    (".//cfdi:Comprobante", "LugarExpedicion", "",
     "LugarDeExpedicion"),  # Corrected output column name
    (".//cfdi:Comprobante", "SubTotal", "0.00", "SubTotal"),
    (".//cfdi:Comprobante", "Descuento", "0.00", "Descuento"),
    (".//cfdi:Comprobante", "Total", "0.00", "Total"),
    (".//cfdi:Comprobante", "Moneda", "", "Moneda"),
    (".//cfdi:Comprobante", "FormaPago", "", "FormaDePago"),
    (".//cfdi:Comprobante", "MetodoPago", "", "Metodo de Pago"),
    (".//cfdi:Comprobante", "Exportacion", "", "Exportacion"),
    (".//cfdi:Comprobante", "CondicionesDePago", "", "Condicion de Pago"),
    (".//cfdi:Comprobante", "TipoCambio", "1.0",
     "Tipo De Cambio"),  # Corrected output column name
    (".//cfdi:Comprobante", "NumCtaPago", "", "NumCtaPago"),

    # CFDI Relacionados
    (".//cfdi:CfdiRelacionados", "TipoRelacion", "", "TipoDeRelacion"),
    # Corrected output column name and XPath to CfdiRelacionado
    (".//cfdi:CfdiRelacionado", "UUID", "", "UUID Relacion"),

    # Emisor
    (".//cfdi:Emisor", "Rfc", "", "RFC Emisor"),
    (".//cfdi:Emisor", "Nombre", "", "Nombre Emisor"),
    (".//cfdi:Emisor", "RegimenFiscal", "", "Regimen Fiscal Emisor"),

    # Receptor
    (".//cfdi:Receptor", "Rfc", "", "RFC Receptor"),
    (".//cfdi:Receptor", "Nombre", "", "Nombre Receptor"),
    # Corrected output column name
    (".//cfdi:Receptor", "UsoCFDI", "", "UsoCFDI"),
    (".//cfdi:Receptor", "ResidenciaFiscal", "", "ResidenciaFiscal"),
    (".//cfdi:Receptor", "NumRegIdTrib", "", "NumRegIdTrib"),
    (".//cfdi:Receptor", "RegimenFiscalReceptor", "", "RegimenFiscalReceptor"),
    (".//cfdi:Receptor", "DomicilioFiscalReceptor", "", "DomicilioFiscalReceptor"),

    # Timbre Fiscal Digital
    # Corrected output column name (was Folio Fiscal)
    (".//tfd:TimbreFiscalDigital", "UUID", "", "UUID"),
    (".//tfd:TimbreFiscalDigital", "FechaTimbrado", "", "Fecha Timbrado"),

    # Impuestos Globales (Totals)
    (".//cfdi:Impuestos", "TotalImpuestosTrasladados", "0.00", "Total Trasladados"),
    (".//cfdi:Impuestos", "TotalImpuestosRetenidos", "0.00", "Total Retenidos"),

    # Implocal complements (Totals)
    (".//implocal:ImpuestosLocales",
     "TotaldeRetenciones", "0.00", "Total LocalRetenido"),
    (".//implocal:ImpuestosLocales", "TotaldeTraslados",
     "0.00", "Total LocalTrasladado"),
]

# List of XML tags/attributes to extract for Nomina complement 1.2 XML.
NOMINA_FIELDS_TO_EXTRACT = [
    (".//nomina12:Nomina", "Version", "", "Version Nomina"),
    (".//nomina12:Nomina", "TipoNomina", "", "Tipo Nomina"),
    (".//nomina12:Nomina", "FechaPago", "", "Fecha Pago"),
    (".//nomina12:Nomina", "FechaInicialPago", "", "Fecha Inicial Pago"),
    (".//nomina12:Nomina", "FechaFinalPago", "", "Fecha Final Pago"),
    # (".//nomina12:Nomina", "NumDiasPagados", "", "Num Dias Pagados"),
    (".//nomina12:Nomina", "TotalPercepciones", "0.00", "Total Sueldos"),
    (".//nomina12:Nomina", "TotalDeducciones", "0.00", "Total Deducciones"),
    (".//nomina12:Nomina", "TotalOtrosPagos", "0.00", "Total Otros Pagos"),
    # Nomina 1.2 Emisor
    (".//nomina12:Emisor", "RegistroPatronal", "", "Registro Patronal"),
    (".//nomina12:Emisor", "Curp", "", "CURP Patron"),
    (".//nomina12:Emisor", "RfcPatronOrigen", "", "RFC Patron"),
    # Nomina 1.2 Receptor
    (".//nomina12:Receptor", "Curp", "", "CURP"),
    (".//nomina12:Receptor", "NumSeguridadSocial", "", "NSS"),
    (".//nomina12:Receptor", "FechaInicioRelLaboral", "", "Inicio Relacion Laboral"),
    # (".//nomina12:Receptor", "Rfc", "", "RFC"), # Already handled by main CFDI RFC Receptor
    # (".//nomina12:Receptor", "TipoContrato", "", "Tipo Contrato"),
    (".//nomina12:Receptor", "Antigüedad", "", "Antiguedad"),
    (".//nomina12:Receptor", "PeriodicidadPago", "", "Periodicidad Pago"),
    # (".//nomina12:Receptor", "Banco", "", "Banco"),
    # (".//nomina12:Receptor", "CuentaBancaria", "", "Cuenta Bancaria"),
    (".//nomina12:Receptor", "SalarioBaseCotApor", "0.00", "SBC"),
    (".//nomina12:Receptor", "SalarioDiarioIntegrado", "0.00", "SDI"),
    (".//nomina12:Receptor", "ClaveEntFed", "", "Entidad"),
    # Nomina 1.2 Deducciones
    # (".//nomina12:Deducciones", "TotalOtrasDeducciones", "0.00", "Total Otras Deducciones"),
    (".//nomina12:Deducciones", "TotalImpuestosRetenidos",
     "0.00", "ImpuestosRetenidos"),  # Corrected output column name
]


def extract_tax_details(root, data):
    """
    Extracts and aggregates various tax details (IVA, IEPS, Retenidos) from XML.
    """
    # Initialize all specific tax fields to "0.00"
    tax_fields = [
        "Total IEPS", "IVA 16%", "Retenido IVA", "Retenido ISR", "ISH",
        "IVA 8%", "IVA Ret 6%", "IEPS 3%", "IEPS 6%", "IEPS 7%", "IEPS 8%",
        "IEPS 9%", "IEPS 26.5%", "IEPS 30%", "IEPS 30.4%", "IEPS 53%", "IEPS 160%",
    ]
    for field in tax_fields:
        data[field] = "0.00"

    # Process Traslados (IVA, IEPS) from global Impuestos and Concepto-level Impuestos
    for traslado in root.findall(".//cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado", NAMESPACES) + \
            root.findall(".//cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado", NAMESPACES):
        impuesto_code = traslado.get("Impuesto", "")
        tipo_factor = traslado.get("TipoFactor", "")
        tasa_ocuota = traslado.get("TasaOCuota", "")
        # Getting raw value, handle None explicitly
        importe_str = traslado.get("Importe")

        # Robust conversion to float, handling None and invalid strings
        try:
            importe = float(importe_str) if importe_str is not None else 0.00
        except (ValueError, TypeError):  # Catch both invalid string and NoneType
            importe = 0.00

        if impuesto_code == "002" and tipo_factor == "Tasa":  # IVA
            if tasa_ocuota == "0.160000":
                data["IVA 16%"] = f"{float(data.get('IVA 16%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.080000":
                data["IVA 8%"] = f"{float(data.get('IVA 8%', '0.00')) + importe:.2f}"
        elif impuesto_code == "003" and tipo_factor == "Tasa":  # IEPS
            # Corrected from Total_IEPS
            data["Total IEPS"] = f"{float(data.get('Total IEPS', '0.00')) + importe:.2f}"
            if tasa_ocuota == "0.030000":
                data["IEPS 3%"] = f"{float(data.get('IEPS 3%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.060000":
                data["IEPS 6%"] = f"{float(data.get('IEPS 6%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.070000":
                data["IEPS 7%"] = f"{float(data.get('IEPS 7%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.080000":
                data["IEPS 8%"] = f"{float(data.get('IEPS 8%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.090000":
                data["IEPS 9%"] = f"{float(data.get('IEPS 9%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.265000":
                data["IEPS 26.5%"] = f"{float(data.get('IEPS 26.5%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.300000":
                data["IEPS 30%"] = f"{float(data.get('IEPS 30%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.304000":
                data["IEPS 30.4%"] = f"{float(data.get('IEPS 30.4%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.530000":
                data["IEPS 53%"] = f"{float(data.get('IEPS 53%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "1.600000":  # Corrected value for 160% IEPS
                data["IEPS 160%"] = f"{float(data.get('IEPS 160%', '0.00')) + importe:.2f}"

    # Process Retenciones (ISR, IVA) from global Impuestos and Concepto-level Impuestos
    for retencion in root.findall(".//cfdi:Impuestos/cfdi:Retenciones/cfdi:Retencion", NAMESPACES) + \
            root.findall(".//cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Retenciones/cfdi:Retencion", NAMESPACES):
        impuesto_code = retencion.get("Impuesto", "")
        # Getting raw value, handle None explicitly
        importe_str = retencion.get("Importe")

        try:
            importe = float(importe_str) if importe_str is not None else 0.00
        except (ValueError, TypeError):
            importe = 0.00

        if impuesto_code == "001":  # ISR
            # Corrected from Retenido_ISR
            data["Retenido ISR"] = f"{float(data.get('Retenido ISR', '0.00')) + importe:.2f}"
        elif impuesto_code == "002":  # IVA
            # Corrected from Retenido_IVA
            data["Retenido IVA"] = f"{float(data.get('Retenido IVA', '0.00')) + importe:.2f}"
            tasa_ocuota_ret = retencion.get("TasaOCuota", "")
            if tasa_ocuota_ret == "0.060000":
                data["IVA Ret 6%"] = f"{float(data.get('IVA Ret 6%', '0.00')) + importe:.2f}"

    # Process the local taxes (ISH)
    # Corrected XPath and logic
    for traslado_local in root.findall(".//implocal:ImpuestosLocales/implocal:TrasladosLocales", NAMESPACES):
        imp_local_trasladado = traslado_local.get("ImpLocTrasladado", "")
        # Getting raw value, handle None explicitly
        importe_str = traslado_local.get("Importe")

        try:
            importe = float(importe_str) if importe_str is not None else 0.00
        except (ValueError, TypeError):
            importe = 0.00

        if imp_local_trasladado == "ISH":
            data["ISH"] = f"{float(data.get('ISH', '0.00')) + importe:.2f}"


def extract_iedu_data(root, data):
    """
    Extracts Specific Data from IEDU Complement
    """
    iedu_complement = root.find(
        ".//cfdi:ComplementoConcepto/iedu:instEducativas", NAMESPACES)  # Corrected XPath for consistency
    if iedu_complement is not None:
        data["CURP Alumno"] = iedu_complement.get(
            "CURP", "")  # Corrected column name
        data["Nivel Educativo"] = iedu_complement.get("nivelEducativo", "")
        data["Nombre Alumno"] = iedu_complement.get(
            "nombreAlumno", "")  # Corrected column name


def parse_xml_invoice(xml_file_path):
    """
    Parses a single XML invoice file, extracts specified fields (data), and determines its type (Invoice or Nomina).
    Merges descriptions from multiple Concepto nodes.

    Args:
        xml_file_path (str): Path to the XML file to be parsed.

    Returns:
        dict: A dictionary containing the extracted data from the XML file.
        Including a "CFDI_Type" key indicating whether it's an "Invoice" or "Nomina".
        None: If the XML file is not valid or does not match expected structure.
    """

    data = {}  # Dictionary to hold the extracted data
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        """
        Initialize all possible fields to None or empty strings.
        This ensures all columns are present even if not populated
        """
        for field in INVOICE_COLUMN_ORDER:  # Corrected variable name here
            # Using None for flexibility. Pandas will convert to NaN/empty for Excel
            data[field] = None

        # Initializes Nomina specific fields too, for consistency across all the processed XMLs
        for _, _, _, col_name in NOMINA_FIELDS_TO_EXTRACT:
            # Ensure Nomina fields are not overwritten if they are also CFDI general fields
            if col_name not in data:  # Check to prevent overwriting common fields
                data[col_name] = None
        data["TotalGravado"] = None
        data["TotalExcento"] = None
        data["TotalDeducciones"] = None
        data["TotalOtrosPagos"] = None

        # Extract CFDI 4.0 fields
        for xpath, attr_name, default_val, col_name in CFDI_FIELDS_TO_EXTRACT:
            element = root.find(xpath, NAMESPACES)
            if element is not None:
                if attr_name:  # If an attribute is specified, get its value
                    value = element.get(attr_name, default_val)
                else:  # It's element text (though most CFDI data is attributes)
                    value = element.text.strip() if element.text is not None else default_val
            else:
                value = default_val
            data[col_name] = value

        # Handle merged "Conceptos" from multiple Concepto nodes
        descriptions = []
        for concepto in root.findall(".//cfdi:Concepto", NAMESPACES):
            description = concepto.get('Descripcion', '').strip()
            if description:
                descriptions.append(description)
        data['Conceptos'] = ' | '.join(
            descriptions) if descriptions else None  # Corrected column name

        # Extract and aggregate tax details.
        extract_tax_details(root, data)

        # Handle implocal:TrasladosLocales (multiple nodes)
        traslados_locales_details = []
        # Corrected XPath
        for traslado_local in root.findall(".//implocal:ImpuestosLocales/implocal:TrasladosLocales", NAMESPACES):
            imp_loc_trasladado = traslado_local.get("ImpLocTrasladado", "")
            tasa_de_traslado = traslado_local.get("TasadeTraslado", "")
            importe = traslado_local.get("Importe", "0.00")  # Ensure default
            traslados_locales_details.append(
                f"{imp_loc_trasladado}|{tasa_de_traslado}|{importe}")
        data["ImpLocal_TrasladosLocales_Details"] = ' | '.join(
            traslados_locales_details) if traslados_locales_details else None

        # Extract Serie and Folio to create the merged "Factura" field
        serie = root.get('Serie', '')
        folio = root.get('Folio', '')
        data['Factura'] = f"{serie}-{folio}".strip() if serie or folio else None

        # Placeholders for fields requiring external logic or not directly in the XML
        data["Verificado ó Asoc."] = ""
        data["Estado SAT"] = ""
        data["EstadoPago"] = ""
        data["FechaPago"] = ""  # Corrected from "Fecha de Pago"
        data["Combustible"] = ""

        # Emisor/Receptor Addresses/Location
        data["Direccion Emisor"] = ""
        data["Localidad Emisor"] = ""
        data["Direccion Receptor"] = ""
        data["Localidad Receptor"] = ""

        # Nomina 1.2 fields
        detected_complements = []
        nomina_complement = root.find(
            './/cfdi:Complemento/nomina12:Nomina', NAMESPACES)
        if nomina_complement is not None:
            data['CFDI_Type'] = 'Nomina'
            detected_complements.append('NOMINA')
            for xpath, attr_name, default_val, col_name in NOMINA_FIELDS_TO_EXTRACT:
                element = root.find(xpath, NAMESPACES)
                if element is not None:
                    if attr_name:
                        value = element.get(attr_name, default_val)
                    else:
                        value = element.text.strip() if element.text is not None else default_val
                else:
                    value = default_val
                data[col_name] = value

            # Calculate TotalGravado and TotalExcento from Percepciones
            total_gravado_percepciones = 0.0
            total_exento_percepciones = 0.0
            for percepcion in root.findall(".//nomina12:Percepcion", NAMESPACES):
                importe_gravado_str = percepcion.get("ImporteGravado")
                importe_exento_str = percepcion.get("ImporteExento")

                try:
                    total_gravado_percepciones += float(
                        importe_gravado_str) if importe_gravado_str is not None else 0.00
                except (ValueError, TypeError):
                    pass
                try:
                    total_exento_percepciones += float(
                        importe_exento_str) if importe_exento_str is not None else 0.00
                except (ValueError, TypeError):
                    pass
            data['TotalGravado'] = f"{total_gravado_percepciones:.2f}"
            data['TotalExcento'] = f"{total_exento_percepciones:.2f}"

        else:  # Default to Invoice if no Nomina complement is found
            data['CFDI_Type'] = 'Invoice'
            for _, _, _, col_name in NOMINA_FIELDS_TO_EXTRACT:
                data[col_name] = None
            data['TotalGravado'] = None
            data['TotalExcento'] = None
            data['TotalDeducciones'] = None
            data['TotalOtrosPagos'] = None

        # Detect other complements and add to the "Complemento" field.
        if root.find('.//cfdi:Complemento/iedu:instEducativas', NAMESPACES) is not None:
            detected_complements.append('IEDU')
            extract_iedu_data(root, data)

        if root.find('.//cfdi:Complemento/implocal:ImpuestosLocales', NAMESPACES) is not None:
            detected_complements.append('IMPLOCAL')

        # Set the complement column
        data["Complemento"] = ", ".join(
            detected_complements) if detected_complements else None

        # "Archivo XML" (filename)
        data['Archivo XML'] = os.path.basename(xml_file_path)

    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file_path}: {e}")
        return None
    except Exception as e:
        print(
            f"An unexpected error occurred while processing {xml_file_path}: {e}")
        return None
    return data
