# --- cfdi_processor/constants.py ---
# This file defines global constants, such as XML namespaces, mapping dictionaries,
# and column orderings used across different modules of the CFDI processor.

# --- XML NAMESPACES ---
# Define XML namespaces for different CFDI versions and complements
NAMESPACES_CFDI_33 = {
    'cfdi': 'http://www.sat.gob.mx/cfd/3',
    'nomina12': 'http://www.sat.gob.mx/nomina12',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
    'iedu': 'http://www.sat.gob.mx/iedu',
    'implocal': 'http://www.sat.gob.mx/implocal',
    # Even if not explicitly used, good to have if present
    'cce11': 'http://www.sat.gob.mx/ComercioExterior11',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

NAMESPACES_CFDI_40 = {
    'cfdi': 'http://www.sat.gob.mx/cfd/4',
    'nomina12': 'http://www.sat.gob.mx/nomina12',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
    'iedu': 'http://www.sat.gob.mx/iedu',
    'implocal': 'http://www.sat.gob.mx/implocal',
    # Even if not explicitly used, good to have if present
    'cce11': 'http://www.sat.gob.mx/ComercioExterior11',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# --- MAPPING DICTIONARIES ---
# Standard SAT catalogs for TipoDeComprobante, FormaPago, MetodoPago, UsoCFDI, RegimenFiscalReceptor

TIPO_COMPROBANTE_MAP = {
    "I": "Factura",     # Ingreso
    "E": "NotaCredito",  # Egreso (Nota de crédito)
    "T": "Traslado",    # Traslado
    "P": "Pago",        # Recepción de pagos
    "N": "Nómina"       # Nómina
}

FORMA_PAGO_MAP = {
    "01": "Efectivo",
    "02": "Cheque nominativo",
    "03": "Transferencia electrónica de fondos",
    "04": "Tarjeta de crédito",
    "05": "Monedero electrónico",
    "06": "Dinero electrónico",
    "08": "Vales de despensa",
    "12": "Dación en pago",
    "13": "Pago por subrogación",
    "14": "Pago por consignación",
    "15": "Condonación",
    "17": "Compensación",
    "23": "Novación",
    "24": "Confusión",
    "25": "Remisión de deuda",
    "26": "Prescripción o caducidad",
    "27": "A satisfacción del acreedor",
    "28": "Tarjeta de débito",
    "29": "Tarjeta de servicios",
    "30": "Aplicación de anticipos",
    "31": "Intermediario pagos",
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
    "D02": "Gastos médicos por incapacidad o discapacidad",
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
    "610": "Residentes en el Extranjero sin Establecimiento Permanente en México",
    "611": "Ingresos por Dividendos (socios y accionistas)",
    "612": "Personas Físicas con Actividades Empresariales y Profesionales",
    "614": "Ingresos por Intereses",
    "615": "Régimen de los ingresos por obtención de premios",
    "616": "Sin Obligaciones Fiscales",
    "620": "Sociedades Cooperativas de Producción que optan por diferir sus ingresos",
    "621": "Incorporación Fiscal",
    "622": "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras",
    "623": "Opcional para Grupos de Sociedades",
    "624": "Coordinados",
    "625": "Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas",
    "626": "Régimen Simplificado de Confianza",
}

# --- COLUMN ORDER DEFINITIONS ---
# Define the precise order of columns for the Invoice sheet.
# This list will be used to ensure the DataFrame columns match this order when exporting to Excel.
INVOICE_COLUMN_ORDER = [
    "Verificado ó Asoc.",
    "Estado SAT",
    "Version",
    "Tipo",
    "Fecha Emision",
    "Fecha Timbrado",
    "EstadoPago",
    "FechaPago",
    "Factura",            # Merged field: Serie + Folio
    "UUID",
    "UUID Relacion",
    # "TipoDeRelacion", # Removed as per user's request to avoid disrupting analysis
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
    "Conceptos",
    "Combustible",
    "IEPS 3%",
    "IEPS 6%",
    "IEPS 7%",
    "IEPS 8%",
    "IEPS 9%",
    "IEPS 26.5%",
    "IEPS 30%",
    "IEPS 30.4%",
    "IEPS 53%",
    "IEPS 160%",
    "Archivo XML",
    "Direccion Emisor",
    "Localidad Emisor",
    "Direccion Receptor",
    "Localidad Receptor",
    "IVA 8%",
    "IVA Ret 6%",
    "RegimenFiscalReceptor",
    "DomicilioFiscalReceptor",
    # "TipoDeRelacion", # Removed as per user's request to avoid disrupting analysis
    "CURP Dependiente",
    "Nivel Educativo",
    "Nombre Dependiente",
]

# --- XML FIELD EXTRACTION DEFINITIONS ---
# List of XML tags/attributes to extract for CFDI elements not directly on the Comprobante root.
# Format: (xpath_to_element, attribute_name_or_None_for_text, default_value, column_name_in_data_dict)
# Note: These generally refer to attributes that do not carry a namespace prefix in the XML attribute name itself.

# Fields common across CFDI versions (3.3 & 4.0) that require explicit XPath
CFDI_COMMON_CHILD_ELEMENTS_TO_EXTRACT = [
    # CFDI Relacionados - TipoRelacion is now excluded from INVOICE_COLUMN_ORDER
    (".//cfdi:CfdiRelacionado", "UUID", "", "UUID Relacion"),
    # Emisor
    (".//cfdi:Emisor", "Rfc", "", "RFC Emisor"),
    (".//cfdi:Emisor", "Nombre", "", "Nombre Emisor"),
    (".//cfdi:Emisor", "RegimenFiscal", "", "RegimenFiscal Emisor"),
    # Receptor
    (".//cfdi:Receptor", "Rfc", "", "RFC Receptor"),
    (".//cfdi:Receptor", "Nombre", "", "Nombre Receptor"),
    (".//cfdi:Receptor", "ResidenciaFiscal", "", "ResidenciaFiscal"),
    (".//cfdi:Receptor", "NumRegIdTrib", "", "NumRegIdTrib"),
    # UsoCFDI and RegimenFiscalReceptor are handled directly in parsing functions with mapping
]

# List of XML tags/attributes to extract for Nomina complement 1.2 XML.
# Format: (xpath_to_element, attribute_name, default_value, column_name_in_data_dict)
NOMINA_FIELDS_TO_EXTRACT = [
    (".//nomina12:Nomina", "Version", "", "Version Nomina"),
    (".//nomina12:Nomina", "TipoNomina", "", "Tipo Nomina"),
    (".//nomina12:Nomina", "FechaPago", "", "Fecha Pago"),
    (".//nomina12:Nomina", "FechaInicialPago", "", "Fecha Inicial Pago"),
    (".//nomina12:Nomina", "FechaFinalPago", "", "Fecha Final Pago"),
    # (".//nomina12:Nomina", "NumDiasPagados", "", "Num Dias Pagados"), # Not in Excel list
    (".//nomina12:Nomina", "TotalPercepciones", "0.00", "Total Sueldos"),
    (".//nomina12:Nomina", "TotalDeducciones", "0.00", "Total Deducciones"),
    (".//nomina12:Nomina", "TotalOtrosPagos", "0.00", "Total Otros Pagos"),
    # Nomina 1.2 Emisor
    (".//nomina12:Emisor", "RegistroPatronal", "", "Registro Patronal"),
    (".//nomina12:Emisor", "Curp", "", "CURP Patron"),
    (".//nomina12:Emisor", "RfcPatronOrigen", "", "RFC Patron"),
    # Nomina 1.2 Receptor
    # This is CURP del Empleado, not Patronal
    (".//nomina12:Receptor", "Curp", "", "CURP"),
    (".//nomina12:Receptor", "NumSeguridadSocial", "", "NSS"),
    (".//nomina12:Receptor", "FechaInicioRelLaboral", "", "Inicio Relacion Laboral"),
    # (".//nomina12:Receptor", "Rfc", "", "RFC"), # Already handled by main CFDI RFC Receptor
    # (".//nomina12:Receptor", "TipoContrato", "", "Tipo Contrato"), # Not in Excel list
    (".//nomina12:Receptor", "Antigüedad", "", "Antiguedad"),
    (".//nomina12:Receptor", "PeriodicidadPago", "", "Periodicidad Pago"),
    # (".//nomina12:Receptor", "Banco", "", "Banco"), # Not in Excel list
    # (".//nomina12:Receptor", "CuentaBancaria", "", "Cuenta Bancaria"), # Not in Excel list
    (".//nomina12:Receptor", "SalarioBaseCotApor", "0.00", "SBC"),
    (".//nomina12:Receptor", "SalarioDiarioIntegrado", "0.00", "SDI"),
    (".//nomina12:Receptor", "ClaveEntFed", "", "Entidad"),
    # Nomina 1.2 Deducciones (TotalImpuestosRetenidos)
    (".//nomina12:Deducciones", "TotalImpuestosRetenidos", "0.00",
     "ImpuestosRetenidos"),  # Column name in Excel is "ImpuestosRetenidos"
    # Nomina Percepciones totals for Gravado and Exento, to be calculated
    # Placeholder for calculated field
    ("TotalGravado", "", "", "TotalGravado"),
    # Placeholder for calculated field
    ("TotalExcento", "", "", "TotalExcento"),
    # Placeholder for calculated field
    ("TotalDeducciones", "", "", "TotalDeducciones"),
    # Placeholder for calculated field
    ("TotalOtrosPagos", "", "", "TotalOtrosPagos"),
]


# Define common ClaveProdServ codes for fuel (from SAT's catalog)
FUEL_PROD_SERV_CODES = ["15101514", "15101501", "15101502", "15101500"]
# Define common units for fuel
FUEL_UNITS = ["LTR", "LITRO", "GAL", "GALON", "KL", "KILO", "KILOGALON", "E48"]
# Define keywords to look for in Description (case-insensitive)
FUEL_KEYWORDS = ["MAGNA", "PREMIUM", "DIESEL",
                 "GASOLINA", "COMBUSTIBLE", "GAS"]
