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
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'pago20': 'http://www.sat.gob.mx/Pagos20'  # New namespace for Pagos 2.0
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
    "CURP Dependiente",
    "Nivel Educativo",
    "Nombre Dependiente",
]

# Define the precise order of columns for the Pagos sheet.
# This list will be used to ensure the DataFrame columns match this order when exporting to Excel.
PAGOS_COLUMN_ORDER = [
    "Verificado o Asoc",
    "Estado SAT",
    "No. Certificado Emisor",
    "No. Certificado SAT",
    "Version CFDI",  # From Comprobante
    "TipoComprobante",
    "Fecha Emision",  # From Comprobante
    "Fecha Timbrado",  # From TimbreFiscalDigital
    "Serie CFDI",  # From Comprobante Serie
    "Folio CFDI",  # From Comprobante Folio
    "UUID CFDI",  # From TimbreFiscalDigital
    "RFC Emisor CFDI",  # From Comprobante Emisor
    "Nombre Emisor CFDI",  # From Comprobante Emisor
    "Regimen Fiscal Emisor CFDI",  # From Comprobante Emisor
    "Lugar de Expedicion CFDI",  # From Comprobante
    "RFC Receptor CFDI",  # From Comprobante Receptor
    "Nombre Receptor CFDI",  # From Comprobante Receptor
    "Regimen Fiscal Receptor CFDI",  # From Comprobante Receptor
    "DomicilioFiscalReceptor CFDI",  # From Comprobante Receptor
    "ResidenciaFiscal CFDI",  # From Comprobante Receptor
    "NumRegIdTrib CFDI",  # From Comprobante Receptor
    "UsoCFDI CFDI",  # From Comprobante Receptor
    "Complementos Comprobante",
    "Archivo XML",
    "Version Pago",  # From pago20:Pagos
    "TotalRetencionesIVA",  # From pago20:ImpuestosP
    "TotalRetencionesISR",  # From pago20:ImpuestosP
    "TotalRetencionesIEPS",  # From pago20:ImpuestosP
    "TotalTrasladosBaseIVA16",  # From pago20:Totales
    "TotalTrasladosImpuestoIVA16",  # From pago20:Totales
    "TotalTrasladosBaseIVA8",  # From pago20:Totales
    "TotalTrasladosImpuestoIVA8",  # From pago20:Totales
    "TotalTrasladosBaseIVA0",  # From pago20:Totales
    "TotalTrasladosImpuestoIVA0",  # From pago20:Totales
    "TotalTrasladadoBaseIVAExento",  # From pago20:Totales
    "MontoTotalPagos",  # From pago20:Totales
    "FechaPago",  # From pago20:Pago
    "FormaDePagoP",  # From pago20:Pago
    "MonedaP",  # From pago20:Pago
    "TipoCambioP",  # From pago20:Pago
    "Monto Pago",  # From pago20:Pago
    "NumOperacion",  # From pago20:Pago
    "RFCEmisorCtaOrd",  # From pago20:Pago
    "NombreBancoOrdExt",  # From pago20:Pago
    "CtaOrdenante",  # From pago20:Pago
    "RFCEmisorCTABen",  # From pago20:Pago
    "CtaBeneficiario",  # From pago20:Pago
    "TipoCadPago",  # From pago20:Pago
    "CertPago",  # From pago20:Pago
    "CadPago",  # From pago20:Pago
    "SelloPago",  # From pago20:Pago
    "IdDocumento Relacionado",  # From pago20:DoctoRelacionado
    "Serie Relacionada",  # From pago20:DoctoRelacionado
    "Folio Relacionado",  # From pago20:DoctoRelacionado
    "MonedaDR",  # From pago20:DoctoRelacionado
    "TipoCambioDR",  # From pago20:DoctoRelacionado
    "EquivalenciaDR",  # From pago20:DoctoRelacionado
    "MetodoDePagoDR",  # From pago20:DoctoRelacionado
    "NumParcialidad",  # From pago20:DoctoRelacionado
    "ImpSaldoAnt",  # From pago20:DoctoRelacionado
    "ImpPagado",  # From pago20:DoctoRelacionado
    "ImpSaldoInsoluto",  # From pago20:DoctoRelacionado
    "ObjetoImpDR",  # From pago20:DoctoRelacionado
    "IVA Excento",  # From pago20:TrasladoDR
    "IVA Excento Base",  # From pago20:TrasladoDR
    "IVA Cero",  # From pago20:TrasladoDR
    "IVA Cero Base",  # From pago20:TrasladoDR
    "IVA 8 Base",  # From pago20:TrasladoDR
    "IVA 8 Importe",  # From pago20:TrasladoDR
    "IVA 16 Base",  # From pago20:TrasladoDR
    "IVA 16 Importe",  # From pago20:TrasladoDR
    "IEPS Cero",  # From pago20:TrasladoDR
    "IEPS Cero Base",  # From pago20:TrasladoDR
    "IEPS 3 Base",  # From pago20:TrasladoDR
    "IEPS 3 Importe",  # From pago20:TrasladoDR
    "IEPS 6 Base",  # From pago20:TrasladoDR
    "IEPS 6 Importe",  # From pago20:TrasladoDR
    "IEPS 7 Base",  # From pago20:TrasladoDR
    "IEPS 7 Importe",  # From pago20:TrasladoDR
    "IEPS 8 Base",  # From pago20:TrasladoDR
    "IEPS 8 Importe",  # From pago20:TrasladoDR
    "IEPS 9 Base",  # From pago20:TrasladoDR
    "IEPS 9 Importe",  # From pago20:TrasladoDR
    "IEPS 25 Base",  # From pago20:TrasladoDR
    "IEPS 25 Importe",  # From pago20:TrasladoDR
    "IEPS 26.5 Base",  # From pago20:TrasladoDR
    "IEPS 26.5 Importe",  # From pago20:TrasladoDR
    "IEPS 30 Base",  # From pago20:TrasladoDR
    "IEPS 30 Importe",  # From pago20:TrasladoDR
    "IEPS 30.4 Base",  # From pago20:TrasladoDR
    "IEPS 30.4 Importe",  # From pago20:TrasladoDR
    "IEPS 50 Base",  # From pago20:TrasladoDR
    "IEPS 50 Importe",  # From pago20:TrasladoDR
    "IEPS 53 Base",  # From pago20:TrasladoDR
    "IEPS 53 Importe",  # From pago20:TrasladoDR
    "IEPS 160 Base",  # From pago20:TrasladoDR
    "IEPS 160 Importe",  # From pago20:TrasladoDR
    "Ret ISR 1.25 Base",  # From pago20:RetencionDR
    "Ret ISR 1.25 Importe",  # From pago20:RetencionDR
    "Ret ISR 10 Base",  # From pago20:RetencionDR
    "Ret ISR 10 Importe",  # From pago20:RetencionDR
    "Ret IVA 4 Base",  # From pago20:RetencionDR
    "Ret IVA 4 Importe",  # From pago20:RetencionDR
    "Ret IVA 10.667 Base",  # From pago20:RetencionDR
    "Ret IVA 10.667 Importe",  # From pago20:RetencionDR
    "Ret IVA 2 Base",  # From pago20:RetencionDR
    "Ret IVA 2 Importe",  # From pago20:RetencionDR
    "Ret IVA 5.33 Base",  # From pago20:RetencionDR
    "Ret IVA 5.33 Importe",  # From pago20:RetencionDR
    "Ret IVA 8 Base",  # From pago20:RetencionDR
    "Ret IVA 8 Importe",  # From pago20:RetencionDR
    "Ret IVA 6 Base",  # From pago20:RetencionDR
    "Ret IVA 6 Importe",  # From pago20:RetencionDR
    "Ret IVA 16 Base",  # From pago20:RetencionDR
    "Ret IVA 16 Importe",  # From pago20:RetencionDR
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

# Fields for the main Pago (pago20:Pago)
PAGO_FIELDS_TO_EXTRACT = [
    # Attributes from pago20:Pagos (main complement)
    (".//pago20:Pagos", "Version", "", "Version Pago"),
    # Attributes from pago20:Totales (nested under Pagos)
    (".//pago20:Totales", "TotalRetencionesIVA", "0.00", "TotalRetencionesIVA"),
    (".//pago20:Totales", "TotalRetencionesISR", "0.00", "TotalRetencionesISR"),
    (".//pago20:Totales", "TotalRetencionesIEPS", "0.00", "TotalRetencionesIEPS"),
    (".//pago20:Totales", "TotalTrasladosBaseIVA16",
     "0.00", "TotalTrasladosBaseIVA16"),
    (".//pago20:Totales", "TotalTrasladosImpuestoIVA16",
     "0.00", "TotalTrasladosImpuestoIVA16"),
    (".//pago20:Totales", "TotalTrasladosBaseIVA8", "0.00", "TotalTrasladosBaseIVA8"),
    (".//pago20:Totales", "TotalTrasladosImpuestoIVA8",
     "0.00", "TotalTrasladosImpuestoIVA8"),
    (".//pago20:Totales", "TotalTrasladosBaseIVA0", "0.00", "TotalTrasladosBaseIVA0"),
    (".//pago20:Totales", "TotalTrasladosImpuestoIVA0",
     "0.00", "TotalTrasladosImpuestoIVA0"),
    (".//pago20:Totales", "TotalTrasladadoBaseIVAExento",
     "0.00", "TotalTrasladadoBaseIVAExento"),
    (".//pago20:Totales", "MontoTotalPagos", "0.00", "MontoTotalPagos"),
    # Attributes from pago20:Pago (individual payment)
    (".//pago20:Pago", "FechaPago", "", "FechaPago"),
    (".//pago20:Pago", "FormaDePagoP", "", "FormaDePagoP"),
    (".//pago20:Pago", "MonedaP", "", "MonedaP"),
    (".//pago20:Pago", "TipoCambioP", "1.0", "TipoCambioP"),
    (".//pago20:Pago", "Monto", "0.00", "Monto Pago"),
    (".//pago20:Pago", "NumOperacion", "", "NumOperacion"),
    (".//pago20:Pago", "RfcEmisorCtaOrd", "", "RFCEmisorCtaOrd"),
    (".//pago20:Pago", "NomBancoOrdExt", "", "NombreBancoOrdExt"),
    (".//pago20:Pago", "CtaOrdenante", "", "CtaOrdenante"),
    (".//pago20:Pago", "RfcEmisorCtaBen", "", "RFCEmisorCTABen"),
    (".//pago20:Pago", "CtaBeneficiario", "", "CtaBeneficiario"),
    (".//pago20:Pago", "TipoCadPago", "", "TipoCadPago"),
    (".//pago20:Pago", "CertPago", "", "CertPago"),
    (".//pago20:Pago", "CadPago", "", "CadPago"),
    (".//pago20:Pago", "SelloPago", "", "SelloPago"),
]

# Fields for DoctoRelacionado (pago20:DoctoRelacionado)
PAGO_DR_FIELDS_TO_EXTRACT = [
    (".//pago20:DoctoRelacionado", "IdDocumento", "", "IdDocumento Relacionado"),
    (".//pago20:DoctoRelacionado", "Serie", "", "Serie Relacionada"),
    (".//pago20:DoctoRelacionado", "Folio", "", "Folio Relacionado"),
    (".//pago20:DoctoRelacionado", "MonedaDR", "", "MonedaDR"),
    (".//pago20:DoctoRelacionado", "TipoCambioDR", "1.0", "TipoCambioDR"),
    (".//pago20:DoctoRelacionado", "EquivalenciaDR", "1.0", "EquivalenciaDR"),
    (".//pago20:DoctoRelacionado", "MetodoDePagoDR", "", "MetodoDePagoDR"),
    (".//pago20:DoctoRelacionado", "NumParcialidad", "", "NumParcialidad"),
    (".//pago20:DoctoRelacionado", "ImpSaldoAnt", "0.00", "ImpSaldoAnt"),
    (".//pago20:DoctoRelacionado", "ImpPagado", "0.00", "ImpPagado"),
    (".//pago20:DoctoRelacionado", "ImpSaldoInsoluto", "0.00", "ImpSaldoInsoluto"),
    (".//pago20:DoctoRelacionado", "ObjetoImpDR", "", "ObjetoImpDR"),
]

# Tax fields within DoctoRelacionado (pago20:ImpuestosDR/TrasladosDR/RetencionesDR)
PAGO_DR_TAX_FIELDS = {
    # TrasladosDR
    "IVA Excento": ("IVA", "Exento", "0.00"),
    "IVA Excento Base": ("IVA", "Exento_Base", "0.00"),
    "IVA Cero": ("IVA", "0.000000_Importe", "0.00"),
    "IVA Cero Base": ("IVA", "0.000000_Base", "0.00"),
    "IVA 8 Base": ("IVA", "0.080000_Base", "0.00"),
    "IVA 8 Importe": ("IVA", "0.080000_Importe", "0.00"),
    "IVA 16 Base": ("IVA", "0.160000_Base", "0.00"),
    "IVA 16 Importe": ("IVA", "0.160000_Importe", "0.00"),

    # IEPS also has Exento (TipoFactor Exento)
    "IEPS Cero": ("IEPS", "Exento", "0.00"),
    "IEPS Cero Base": ("IEPS", "Exento_Base", "0.00"),
    "IEPS 3 Base": ("IEPS", "0.030000_Base", "0.00"),
    "IEPS 3 Importe": ("IEPS", "0.030000_Importe", "0.00"),
    "IEPS 6 Base": ("IEPS", "0.060000_Base", "0.00"),
    "IEPS 6 Importe": ("IEPS", "0.060000_Importe", "0.00"),
    "IEPS 7 Base": ("IEPS", "0.070000_Base", "0.00"),
    "IEPS 7 Importe": ("IEPS", "0.070000_Importe", "0.00"),
    "IEPS 8 Base": ("IEPS", "0.080000_Base", "0.00"),
    "IEPS 8 Importe": ("IEPS", "0.080000_Importe", "0.00"),
    "IEPS 9 Base": ("IEPS", "0.090000_Base", "0.00"),
    "IEPS 9 Importe": ("IEPS", "0.090000_Importe", "0.00"),
    # Example, confirm actual rates
    "IEPS 25 Base": ("IEPS", "0.250000_Base", "0.00"),
    "IEPS 25 Importe": ("IEPS", "0.250000_Importe", "0.00"),
    "IEPS 26.5 Base": ("IEPS", "0.265000_Base", "0.00"),
    "IEPS 26.5 Importe": ("IEPS", "0.265000_Importe", "0.00"),
    "IEPS 30 Base": ("IEPS", "0.300000_Base", "0.00"),
    "IEPS 30 Importe": ("IEPS", "0.300000_Importe", "0.00"),
    "IEPS 30.4 Base": ("IEPS", "0.304000_Base", "0.00"),
    "IEPS 30.4 Importe": ("IEPS", "0.304000_Importe", "0.00"),
    # Example, confirm actual rates
    "IEPS 50 Base": ("IEPS", "0.500000_Base", "0.00"),
    "IEPS 50 Importe": ("IEPS", "0.500000_Importe", "0.00"),
    "IEPS 53 Base": ("IEPS", "0.530000_Base", "0.00"),
    "IEPS 53 Importe": ("IEPS", "0.530000_Importe", "0.00"),
    "IEPS 160 Base": ("IEPS", "1.600000_Base", "0.00"),
    "IEPS 160 Importe": ("IEPS", "1.600000_Importe", "0.00"),

    # RetencionesDR
    # Assuming 1.25% for ISR
    "Ret ISR 1.25 Base": ("ISR", "0.012500_Base", "0.00"),
    "Ret ISR 1.25 Importe": ("ISR", "0.012500_Importe", "0.00"),
    # Assuming 10% for ISR
    "Ret ISR 10 Base": ("ISR", "0.100000_Base", "0.00"),
    "Ret ISR 10 Importe": ("ISR", "0.100000_Importe", "0.00"),

    "Ret IVA 4 Base": ("IVA", "0.040000_Base", "0.00"),  # Assuming 4% for IVA
    "Ret IVA 4 Importe": ("IVA", "0.040000_Importe", "0.00"),
    # Assuming 10.667% for IVA
    "Ret IVA 10.667 Base": ("IVA", "0.106667_Base", "0.00"),
    "Ret IVA 10.667 Importe": ("IVA", "0.106667_Importe", "0.00"),
    "Ret IVA 2 Base": ("IVA", "0.020000_Base", "0.00"),  # Assuming 2% for IVA
    "Ret IVA 2 Importe": ("IVA", "0.020000_Importe", "0.00"),
    # Assuming 5.33% for IVA
    "Ret IVA 5.33 Base": ("IVA", "0.053333_Base", "0.00"),
    "Ret IVA 5.33 Importe": ("IVA", "0.053333_Importe", "0.00"),
    "Ret IVA 8 Base": ("IVA", "0.080000_Base", "0.00"),  # Assuming 8% for IVA
    "Ret IVA 8 Importe": ("IVA", "0.080000_Importe", "0.00"),
    "Ret IVA 6 Base": ("IVA", "0.060000_Base", "0.00"),  # Assuming 6% for IVA
    "Ret IVA 6 Importe": ("IVA", "0.060000_Importe", "0.00"),
    # Assuming 16% for IVA
    "Ret IVA 16 Base": ("IVA", "0.160000_Base", "0.00"),
    "Ret IVA 16 Importe": ("IVA", "0.160000_Importe", "0.00"),
}


# Define common ClaveProdServ codes for fuel (from SAT's catalog)
FUEL_PROD_SERV_CODES = ["15101514", "15101501", "15101502", "15101500"]
# Define common units for fuel
FUEL_UNITS = ["LTR", "LITRO", "GAL", "GALON", "KL", "KILO", "KILOGALON", "E48"]
# Define keywords to look for in Description (case-insensitive)
FUEL_KEYWORDS = ["MAGNA", "PREMIUM", "DIESEL",
                 "GASOLINA", "COMBUSTIBLE", "GAS"]
