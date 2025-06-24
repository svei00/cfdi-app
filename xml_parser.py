# --- cfdi_processor/xml_parser.py ---
# ----------XML Processor----------
# source: http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd
import xml.etree.ElementTree as ET
import os
from datetime import datetime  # Import datetime for date formatting

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
    # For Combustible detection (ComercioExterior 1.1) - not used for primary fuel detection
    'cce11': 'http://www.sat.gob.mx/ComercioExterior11',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# Define the full URI for the CFDI namespace for direct attribute access
# Get the URI directly from the NAMESPACES dictionary
CFDI_URI = NAMESPACES['cfdi']
TFD_URI = NAMESPACES['tfd']

# --- MAPPING DICTIONARIES ---
# Standard SAT catalogs for TipoDeComprobante, FormaPago, MetodoPago, UsoCFDI
TIPO_COMPROBANTE_MAP = {
    "I": "Factura",  # Ingreso
    "E": "NotaCredito",  # Egreso (Nota de crédito)
    "T": "Traslado",  # Traslado
    "P": "Pago",    # Recepción de pagos
    "N": "Nómina"   # Nómina (though handled by CFDI_Type in this app)
}

FORMA_PAGO_MAP = {
    "01": "Efectivo",
    "02": "Cheque nominativo",
    "03": "Transferencia electrónica de fondos",
    "04": "Tarjeta de crédito",
    "05": "Monedero electrónico",
    "06": "Dinero electrónico",
    "08": "Tarjeta de débito",
    "12": "Dación en pago",
    "13": "Pago por subrogación",
    "14": "Pago por consignación",
    "15": "Condenación o remisión de deuda",
    "17": "Compensación",
    "23": "Novación",
    "24": "Confusión",
    "25": "Condonación",
    "26": "Remisión de deuda",
    "27": "Prescripción o caducidad",
    "28": "Tarjeta de servicios",
    "29": "Aplicación de anticipos",
    "30": "Documento bancario",
    "31": "Intermediario de pagos",
    "99": "Por definir"
}

METODO_PAGO_MAP = {
    "PUE": "Pago en una sola exhibición",
    "PPD": "Pago en parcialidades o diferido"
}

USO_CFDI_MAP = {
    "G01": "Adquisición de mercancías",
    "G02": "Devoluciones, descuentos o bonificaciones",
    "G03": "Gastos en general",
    "I01": "Construcciones",
    "I02": "Mobiliario y equipo de oficina por inversiones",
    "I03": "Equipo de transporte",
    "I04": "Equipo de cómputo y accesorios",
    "I05": "Dados, troqueles, moldes, matrices y herramental",
    "I06": "Comunicaciones telefónicas",
    "I07": "Comunicaciones satelitales",
    "I08": "Otra maquinaria y equipo",
    "D01": "Honorarios médicos, dentales y gastos hospitalarios",
    "D02": "Gastos médicos por incapacidad or disability",
    "D03": "Gastos funerales",
    "D04": "Donativos",
    "D05": "Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)",
    "D06": "Aportaciones voluntarias al SAR",
    "D07": "Primas por seguros de gastos médicos",
    "D08": "Gastos de transportación escolar obligatoria",
    "D09": "Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones",
    "D10": "Pagos por servicios educativos (colegiaturas)",
    "S01": "Sin efectos fiscales",
    "CP01": "Pagos",
    "CN01": "Nómina",
}

REGIMEN_FISCAL_RECEPTOR_MAP = {
    "601": "General de Ley Personas Morales",
    "603": "Personas Morales con Fines no Lucrativos",
    "605": "Sueldos y Salarios e Ingresos Asimilados a Salarios",
    "606": "Arrendamiento",
    "607": "Régimen de Enajenación o Adquisición de Bienes",
    "608": "Demas ingresos",
    "609": "Consolidación",
    "610": "Residentes en el Extranjero sin Establecimiento Permanente en México",
    "611": "Ingresos por Dividendos (socios y accionistas)",
    "612": "Personas Físicas con Actividades Empresariales y Profesionales",
    "614": "Ingresos por Intereses",
    "615": "Régimen de los Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras",
    "616": "Sin Obligaciones Fiscales",
    "620": "Sociedades Cooperativas de Producción que optan por diferir sus ingresos",
    "621": "Incorporación Fiscal",
    "622": "Actividades Empresariales con ingresos a través de Plataformas Tecnológicas",
    "623": "Simplificado de Confianza",
    "624": "Plataformas Tecnológicas"  # This could be similar to 622
}
# --- END MAPPING DICTIONARIES ---

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
    "UUID Relacion",
    "RFC Emisor",
    "Nombre Emisor",
    "LugarDeExpedicion",
    "RFC Receptor",
    "Nombre Receptor",
    "ResidenciaFiscal",
    "NumRegIdTrib",
    "UsoCFDI",  # This will now be mapped to include description
    "SubTotal",
    "Descuento",
    "Total IEPS",
    "IVA 16%",
    "Retenido IVA",
    "Retenido ISR",
    "ISH",
    "Total",
    "Total Trasladados",  # Re-added for explicit extraction
    "Total Retenidos",   # Re-added for explicit extraction
    "Total LocalTrasladado",
    "Total LocalRetenido",
    "Complemento",
    "Moneda",
    "Tipo De Cambio",
    "FormaDePago",
    "Metodo de Pago",
    "NumCtaPago",
    "Condicion de Pago",
    "Conceptos",
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
    "Direccion Emisor",
    "Localidad Emisor",
    "Direccion Receptor",
    "Localidad Receptor",
    "IVA 8%",
    "IEPS 30.4%",
    "IVA Ret 6%",
    "RegimenFiscalReceptor",  # This will now be mapped to include description
    "DomicilioFiscalReceptor",
    "CURP Dependiente",  # Reverted to Dependiente
    "Nivel Educativo",
    "Nombre Dependiente",  # Reverted to Dependiente
]

# List of XML tags/attributes to extract for CFDI elements not directly on the Comprobante root.
# Note: These attributes do not carry a namespace prefix in the XML, even if their parent element does.
CFDI_CHILD_ELEMENTS_TO_EXTRACT = [
    # CFDI Relacionados
    (".//cfdi:CfdiRelacionados", "TipoRelacion", "", "TipoDeRelacion"),
    (".//cfdi:CfdiRelacionado", "UUID", "", "UUID Relacion"),

    # Emisor
    (".//cfdi:Emisor", "Rfc", "", "RFC Emisor"),
    (".//cfdi:Emisor", "Nombre", "", "Nombre Emisor"),
    (".//cfdi:Emisor", "RegimenFiscal", "", "Regimen Fiscal Emisor"),

    # Receptor
    (".//cfdi:Receptor", "Rfc", "", "RFC Receptor"),
    (".//cfdi:Receptor", "Nombre", "", "Nombre Receptor"),
    (".//cfdi:Receptor", "ResidenciaFiscal", "", "ResidenciaFiscal"),
    (".//cfdi:Receptor", "NumRegIdTrib", "", "NumRegIdTrib"),
    # UsoCFDI and RegimenFiscalReceptor are handled directly in parse_xml_invoice with mapping
    (".//cfdi:Receptor", "DomicilioFiscalReceptor",
     "", "DomicilioFiscalReceptor"),  # Postal Code
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
     "0.00", "ImpuestosRetenidos"),
]


def extract_tax_details(root, data):
    """
    Extracts and aggregates various tax details (IVA, IEPS, Retenidos, Local Taxes) from XML.
    Correctly extracts TotalImpuestosTrasladados and TotalImpuestosRetenidos
    from the global cfdi:Impuestos element's attributes.
    """
    # Initialize all specific tax fields to "0.00"
    tax_fields = [
        "Total IEPS", "IVA 16%", "Retenido IVA", "Retenido ISR", "ISH",
        "IVA 8%", "IVA Ret 6%", "IEPS 3%", "IEPS 6%", "IEPS 7%", "IEPS 8%",
        "IEPS 9%", "IEPS 26.5%", "IEPS 30%", "IEPS 30.4%", "IEPS 53%", "IEPS 160%",
    ]
    for field in tax_fields:
        data[field] = "0.00"

    # --- Extract TotalImpuestosTrasladados and TotalImpuestosRetenidos from global cfdi:Impuestos attributes ---
    global_impuestos_element = root.find("./cfdi:Impuestos", NAMESPACES)

    if global_impuestos_element is not None:
        # Directly get the attributes from the global cfdi:Impuestos element
        total_trasladados_str = global_impuestos_element.get(
            "TotalImpuestosTrasladados", "0.00").strip()
        total_retenidos_str = global_impuestos_element.get(
            "TotalImpuestosRetenidos", "0.00").strip()

        try:
            data["Total Trasladados"] = f"{float(total_trasladados_str):.2f}"
        except (ValueError, TypeError):
            data["Total Trasladados"] = "0.00"

        try:
            data["Total Retenidos"] = f"{float(total_retenidos_str):.2f}"
        except (ValueError, TypeError):
            data["Total Retenidos"] = "0.00"
    else:
        # If no global cfdi:Impuestos element, these totals are zero
        data["Total Trasladados"] = "0.00"
        data["Total Retenidos"] = "0.00"

    # --- Process Specific Traslados (IVA, IEPS) from Conceptos ONLY ---
    # This section sums up the individual tax amounts per concept.
    for concepto_traslado in root.findall(".//cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado", NAMESPACES):
        impuesto_code = concepto_traslado.get("Impuesto", "").strip()
        tipo_factor = concepto_traslado.get("TipoFactor", "").strip()
        tasa_ocuota = concepto_traslado.get("TasaOCuota", "").strip()
        importe_str = concepto_traslado.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        if impuesto_code == "002" and tipo_factor == "Tasa":  # IVA
            if tasa_ocuota == "0.160000":
                data["IVA 16%"] = f"{float(data.get('IVA 16%', '0.00')) + importe:.2f}"
            elif tasa_ocuota == "0.080000":
                data["IVA 8%"] = f"{float(data.get('IVA 8%', '0.00')) + importe:.2f}"
        elif impuesto_code == "003" and tipo_factor == "Tasa":  # IEPS
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
            elif tasa_ocuota == "1.600000":
                data["IEPS 160%"] = f"{float(data.get('IEPS 160%', '0.00')) + importe:.2f}"

    # --- Process Specific Retenciones (ISR, IVA) from Conceptos ONLY ---
    for concepto_retencion in root.findall(".//cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Retenciones/cfdi:Retencion", NAMESPACES):
        impuesto_code = concepto_retencion.get("Impuesto", "").strip()
        importe_str = concepto_retencion.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        if impuesto_code == "001":  # ISR
            data["Retenido ISR"] = f"{float(data.get('Retenido ISR', '0.00')) + importe:.2f}"
        elif impuesto_code == "002":  # IVA
            data["Retenido IVA"] = f"{float(data.get('Retenido IVA', '0.00')) + importe:.2f}"
            tasa_ocuota_ret = concepto_retencion.get("TasaOCuota", "").strip()
            if tasa_ocuota_ret == "0.060000":
                data["IVA Ret 6%"] = f"{float(data.get('IVA Ret 6%', '0.00')) + importe:.2f}"

    # --- Process Local Taxes (ISH, Total LocalTrasladado, Total LocalRetenido) ---
    total_local_trasladado_sum = 0.0
    for traslado_local in root.findall(".//implocal:ImpuestosLocales/implocal:TrasladosLocales", NAMESPACES):
        imp_loc_trasladado = traslado_local.get("ImpLocTrasladado", "").strip()
        tasa_de_traslado = traslado_local.get("TasadeTraslado", "").strip()
        importe_str = traslado_local.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        if imp_loc_trasladado == "ISH":
            data["ISH"] = f"{float(data.get('ISH', '0.00')) + importe:.2f}"
        total_local_trasladado_sum += importe

    data["Total LocalTrasladado"] = f"{total_local_trasladado_sum:.2f}"

    total_local_retenido_sum = 0.0
    for retencion_local in root.findall(".//implocal:ImpuestosLocales/implocal:RetencionesLocales", NAMESPACES):
        # Make sure to get the correct attribute name
        imp_local_retenido = retencion_local.get("ImpLocRetenido", "").strip()
        importe_str = retencion_local.get("Importe", "0.00").strip()

        try:
            importe = float(importe_str)
        except (ValueError, TypeError):
            importe = 0.00

        total_local_retenido_sum += importe
    data["Total LocalRetenido"] = f"{total_local_retenido_sum:.2f}"


def extract_iedu_data(root, data):
    """
    Extracts Specific Data from IEDU Complement
    This function expects the root of the XML (cfdi:Comprobante) and navigates from there.
    """
    # Corrected XPath to find iedu:instEducativas nested under cfdi:Concepto/cfdi:ComplementoConcepto
    iedu_complement = root.find(
        ".//cfdi:Concepto/cfdi:ComplementoConcepto/iedu:instEducativas", NAMESPACES)
    if iedu_complement is not None:
        data["CURP Dependiente"] = iedu_complement.get("CURP", "").strip()
        data["Nivel Educativo"] = iedu_complement.get(
            "nivelEducativo", "").strip()
        data["Nombre Dependiente"] = iedu_complement.get(
            "nombreAlumno", "").strip()


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
        Initialize all possible fields to None.
        This ensures all columns are present even if not populated
        """
        for field in INVOICE_COLUMN_ORDER:
            data[field] = None

        # --- Explicitly Extract Root-Level CFDI Comprobante Attributes ---
        # These attributes are on the namespaced <cfdi:Comprobante> element,
        # but the attributes themselves are NOT namespaced in the XML (e.g., Version="4.0" not cfdi:Version="4.0").
        # Therefore, use plain .get() without the URI prefix.
        data["Version"] = root.get("Version", "4.0").strip()
        # Use .get() without URI prefix as TipoDeComprobante is not namespaced in XML
        tipo_comprobante_code = root.get("TipoDeComprobante", "").strip()
        data["Tipo"] = TIPO_COMPROBANTE_MAP.get(
            tipo_comprobante_code, "Desconocido")

        # Fecha Emision
        fecha_emision_raw = root.get("Fecha", "").strip()
        if fecha_emision_raw:
            try:
                dt_object = datetime.strptime(
                    fecha_emision_raw, "%Y-%m-%dT%H:%M:%S")
                data["Fecha Emision"] = dt_object.strftime("%d/%m/%Y")
            except ValueError:
                data["Fecha Emision"] = ""

        # SubTotal
        subtotal_str = root.get("SubTotal", "0.00").strip()
        try:
            data["SubTotal"] = f"{float(subtotal_str):.2f}"
        except (ValueError, TypeError):
            data["SubTotal"] = "0.00"

        # Descuento
        descuento_str = root.get("Descuento", "0.00").strip()
        try:
            data["Descuento"] = f"{float(descuento_str):.2f}"
        except (ValueError, TypeError):
            data["Descuento"] = "0.00"

        # Total
        total_str = root.get("Total", "0.00").strip()
        try:
            data["Total"] = f"{float(total_str):.2f}"
        except (ValueError, TypeError):
            data["Total"] = "0.00"

        data["Moneda"] = root.get("Moneda", "").strip()
        data["Tipo De Cambio"] = root.get("TipoCambio", "1.0").strip()

        # FormaDePago
        forma_pago_code = root.get("FormaPago", "").strip()
        data["FormaDePago"] = f"{forma_pago_code} - {FORMA_PAGO_MAP.get(forma_pago_code, 'Desconocido')}" if forma_pago_code else None

        # Metodo de Pago
        metodo_pago_code = root.get("MetodoPago", "").strip()
        data["Metodo de Pago"] = f"{metodo_pago_code} - {METODO_PAGO_MAP.get(metodo_pago_code, 'Desconocido')}" if metodo_pago_code else None

        data["LugarDeExpedicion"] = root.get("LugarExpedicion", "").strip()
        data["Condicion de Pago"] = root.get(
            "CondicionesDePago", "").strip()  # Note XML is CondicionesDePago
        data["NumCtaPago"] = root.get("NumCtaPago", "").strip()
        data["Exportacion"] = root.get("Exportacion", "").strip()

        # --- Extract Timbre Fiscal Digital Attributes ---
        # Attributes on tfd:TimbreFiscalDigital are also NOT namespaced (e.g., UUID="...", not tfd:UUID="...").
        timbre_fiscal_digital = root.find(
            ".//tfd:TimbreFiscalDigital", NAMESPACES)
        if timbre_fiscal_digital is not None:
            data["UUID"] = timbre_fiscal_digital.get("UUID", "").strip()
            fecha_timbrado_raw = timbre_fiscal_digital.get(
                "FechaTimbrado", "").strip()
            if fecha_timbrado_raw:
                try:
                    dt_object = datetime.strptime(
                        fecha_timbrado_raw, "%Y-%m-%dT%H:%M:%S")
                    data["Fecha Timbrado"] = dt_object.strftime(
                        "%d/%m/%Y %H:%M:%S")
                except ValueError:
                    data["Fecha Timbrado"] = ""
        # --- End Explicit Extraction for root/timbre attributes ---

        # Extract other child elements from CFDI_CHILD_ELEMENTS_TO_EXTRACT
        # These generally refer to attributes that don't need special namespace handling on the attribute name itself
        for xpath, attr_name, default_val, col_name in CFDI_CHILD_ELEMENTS_TO_EXTRACT:
            element = root.find(xpath, NAMESPACES)
            if element is not None:
                if attr_name:
                    # Access attribute without URI prefix as it is not namespaced in XML
                    value = element.get(attr_name, default_val).strip() if element.get(
                        attr_name) is not None else default_val
                else:
                    value = element.text.strip() if element.text is not None else default_val
            else:
                value = default_val
            data[col_name] = value

        # --- UsoCFDI mapping ---
        # Special handling for UsoCFDI since its mapping is external
        # The UsoCFDI attribute is on the Receptor element, which itself is namespaced by cfdi.
        # The attribute "UsoCFDI" itself is NOT namespaced (no cfdi:UsoCFDI in XML).
        uso_cfdi_element = root.find(".//cfdi:Receptor", NAMESPACES)
        if uso_cfdi_element is not None:
            uso_cfdi_code = uso_cfdi_element.get("UsoCFDI", "").strip()
            if uso_cfdi_code:
                data["UsoCFDI"] = f"{uso_cfdi_code} - {USO_CFDI_MAP.get(uso_cfdi_code, 'Desconocido')}"
            else:
                data["UsoCFDI"] = None
        else:
            # Ensure it's explicitly None if receptor not found
            data["UsoCFDI"] = None

        # --- RegimenFiscalReceptor mapping ---
        regimen_fiscal_receptor_element = root.find(
            ".//cfdi:Receptor", NAMESPACES)
        if regimen_fiscal_receptor_element is not None:
            regimen_code = regimen_fiscal_receptor_element.get(
                "RegimenFiscalReceptor", "").strip()
            if regimen_code:
                data[
                    "RegimenFiscalReceptor"] = f"{regimen_code} - {REGIMEN_FISCAL_RECEPTOR_MAP.get(regimen_code, 'Desconocido')}"
            else:
                data["RegimenFiscalReceptor"] = None
        else:
            data["RegimenFiscalReceptor"] = None

        # Handle merged "Conceptos" from multiple Concepto nodes
        descriptions = []
        for concepto in root.findall(".//cfdi:Concepto", NAMESPACES):
            description = concepto.get('Descripcion', '').strip()
            if description:
                descriptions.append(description)
        data['Conceptos'] = ' | '.join(descriptions) if descriptions else None

        # Extract and aggregate tax details.
        # This function handles Total Trasladados/Retenidos and others
        extract_tax_details(root, data)

        # Handle implocal:TrasladosLocales (multiple nodes) - details for debugging, not direct output column
        traslados_locales_details = []
        for traslado_local in root.findall(".//implocal:ImpuestosLocales/implocal:TrasladosLocales", NAMESPACES):
            imp_loc_trasladado = traslado_local.get(
                "ImpLocTrasladado", "").strip()
            tasa_de_traslado = traslado_local.get("TasadeTraslado", "").strip()
            importe = traslado_local.get("Importe", "0.00").strip()
            traslados_locales_details.append(
                f"{imp_loc_trasladado}|{tasa_de_traslado}|{importe}")
        data["ImpLocal_TrasladosLocales_Details"] = ' | '.join(
            traslados_locales_details) if traslados_locales_details else None

        # Extract Serie and Folio to create the merged "Factura" field
        # These are directly on the Comprobante element, so use plain .get()
        serie = root.get("Serie", '').strip()
        folio = root.get("Folio", '').strip()

        # --- FIX for Factura field formatting (Serie-Folio vs Folio) ---
        if serie and folio:
            data['Factura'] = f"{serie}-{folio}"
        elif folio:  # Only folio exists
            data['Factura'] = folio
        else:  # Both are empty
            data['Factura'] = None
        # --- END FIX ---

        # Placeholders for fields requiring external logic or not directly in the XML
        data["Verificado ó Asoc."] = ""
        data["Estado SAT"] = ""
        data["EstadoPago"] = ""
        data["FechaPago"] = ""

        # --- Combustible Detection Logic ---
        # Define common ClaveProdServ codes for fuel (from SAT's catalog)
        fuel_prod_serv_codes = ["15101514", "15101501", "15101502", "15101500"]
        # Define common units for fuel
        fuel_units = ["LTR", "LITRO", "GAL", "GALON", "KL", "KILO",
                      "KILOGALON", "E48"]  # Added 'E48' as per your XML example
        # Define keywords to look for in Description (case-insensitive)
        fuel_keywords = ["MAGNA", "PREMIUM", "DIESEL",
                         "GASOLINA", "COMBUSTIBLE", "GAS"]

        combustible_detected = False
        for concepto in root.findall(".//cfdi:Concepto", NAMESPACES):
            clave_prod_serv = concepto.get("ClaveProdServ", "").strip()
            # Correctly use ClaveUnidad and strip()
            unidad = concepto.get("ClaveUnidad", "").upper().strip()
            description = concepto.get("Descripcion", "").upper().strip()

            # Primary check: By Product/Service Code
            if clave_prod_serv in fuel_prod_serv_codes:
                combustible_detected = True
                break

            # Secondary check: By Unit and Keywords in Description
            if unidad in fuel_units and any(keyword in description for keyword in fuel_keywords):
                combustible_detected = True
                break

        data["Combustible"] = "Yes" if combustible_detected else "No"
        # --- End Combustible Detection Logic ---

        # Emisor/Receptor Addresses/Location (Placeholders)
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
                        value = element.get(attr_name, default_val).strip() if element.get(
                            attr_name) is not None else default_val  # Added strip()
                    else:
                        value = element.text.strip() if element.text is not None else default_val
                else:
                    value = default_val
                data[col_name] = value

            # Calculate TotalGravado and TotalExcento from Percepciones
            total_gravado_percepciones = 0.0
            total_exento_percepciones = 0.0
            for percepcion in root.findall(".//nomina12:Percepcion", NAMESPACES):
                importe_gravado_str = percepcion.get(
                    "ImporteGravado", "0.00").strip()
                importe_exento_str = percepcion.get(
                    "ImporteExento", "0.00").strip()

                try:
                    total_gravado_percepciones += float(importe_gravado_str)
                except (ValueError, TypeError):
                    pass
                try:
                    total_exento_percepciones += float(importe_exento_str)
                except (ValueError, TypeError):
                    pass
            data['TotalGravado'] = f"{total_gravado_percepciones:.2f}"
            data['TotalExcento'] = f"{total_exento_percepciones:.2f}"

        else:  # Default to Invoice if no Nomina complement is found
            data['CFDI_Type'] = 'Invoice'
            # Ensure Nomina specific fields are explicitly None for non-Nomina CFDI
            for _, _, _, col_name in NOMINA_FIELDS_TO_EXTRACT:
                data[col_name] = None
            data['TotalGravado'] = None
            data['TotalExcento'] = None
            data['TotalDeducciones'] = None
            data['TotalOtrosPagos'] = None

        # Detect other complements and add to the "Complemento" field.
        # This part is updated to correctly find IEDU under Concepto/ComplementoConcepto
        if root.find('.//cfdi:Concepto/cfdi:ComplementoConcepto/iedu:instEducativas', NAMESPACES) is not None:
            detected_complements.append('IEDU')
            # Call extract_iedu_data which now uses the correct XPath
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
