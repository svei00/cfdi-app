# Esquemas oficiales SAT — referencia extraída (2026-07-04)

> Generado PROGRAMÁTICAMENTE desde los XSD oficiales en `docs/` — no a mano.
> Fuente de verdad para F2.6 (captura de campos) y la auditoría de ROADMAP §13.
> `[REQ]` = atributo obligatorio según el SAT; `[opt]` = opcional.

## CFDI 4.0 — Comprobante (núcleo) (`docs/cfdv40.xsd`)

```
ELEM  /Comprobante
ELEM  /Comprobante/InformacionGlobal
attr  /Comprobante/InformacionGlobal@Periodicidad [REQ]
attr  /Comprobante/InformacionGlobal@Meses [REQ]
attr  /Comprobante/InformacionGlobal@Año [REQ]
ELEM  /Comprobante/CfdiRelacionados
ELEM  /Comprobante/CfdiRelacionados/CfdiRelacionado
attr  /Comprobante/CfdiRelacionados/CfdiRelacionado@UUID [REQ]
attr  /Comprobante/CfdiRelacionados@TipoRelacion [REQ]
ELEM  /Comprobante/Emisor
attr  /Comprobante/Emisor@Rfc [REQ]
attr  /Comprobante/Emisor@Nombre [REQ]
attr  /Comprobante/Emisor@RegimenFiscal [REQ]
attr  /Comprobante/Emisor@FacAtrAdquirente [opt]
ELEM  /Comprobante/Receptor
attr  /Comprobante/Receptor@Rfc [REQ]
attr  /Comprobante/Receptor@Nombre [REQ]
attr  /Comprobante/Receptor@DomicilioFiscalReceptor [REQ]
attr  /Comprobante/Receptor@ResidenciaFiscal [opt]
attr  /Comprobante/Receptor@NumRegIdTrib [opt]
attr  /Comprobante/Receptor@RegimenFiscalReceptor [REQ]
attr  /Comprobante/Receptor@UsoCFDI [REQ]
ELEM  /Comprobante/Conceptos
ELEM  /Comprobante/Conceptos/Concepto
ELEM  /Comprobante/Conceptos/Concepto/Impuestos
ELEM  /Comprobante/Conceptos/Concepto/Impuestos/Traslados
ELEM  /Comprobante/Conceptos/Concepto/Impuestos/Traslados/Traslado
attr  /Comprobante/Conceptos/Concepto/Impuestos/Traslados/Traslado@Base [REQ]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Traslados/Traslado@Impuesto [REQ]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Traslados/Traslado@TipoFactor [REQ]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Traslados/Traslado@TasaOCuota [opt]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Traslados/Traslado@Importe [opt]
ELEM  /Comprobante/Conceptos/Concepto/Impuestos/Retenciones
ELEM  /Comprobante/Conceptos/Concepto/Impuestos/Retenciones/Retencion
attr  /Comprobante/Conceptos/Concepto/Impuestos/Retenciones/Retencion@Base [REQ]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Retenciones/Retencion@Impuesto [REQ]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Retenciones/Retencion@TipoFactor [REQ]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Retenciones/Retencion@TasaOCuota [REQ]
attr  /Comprobante/Conceptos/Concepto/Impuestos/Retenciones/Retencion@Importe [REQ]
ELEM  /Comprobante/Conceptos/Concepto/ACuentaTerceros
attr  /Comprobante/Conceptos/Concepto/ACuentaTerceros@RfcACuentaTerceros [REQ]
attr  /Comprobante/Conceptos/Concepto/ACuentaTerceros@NombreACuentaTerceros [REQ]
attr  /Comprobante/Conceptos/Concepto/ACuentaTerceros@RegimenFiscalACuentaTerceros [REQ]
attr  /Comprobante/Conceptos/Concepto/ACuentaTerceros@DomicilioFiscalACuentaTerceros [REQ]
ELEM  /Comprobante/Conceptos/Concepto/InformacionAduanera
attr  /Comprobante/Conceptos/Concepto/InformacionAduanera@NumeroPedimento [REQ]
ELEM  /Comprobante/Conceptos/Concepto/CuentaPredial
attr  /Comprobante/Conceptos/Concepto/CuentaPredial@Numero [REQ]
ELEM  /Comprobante/Conceptos/Concepto/ComplementoConcepto
ELEM  /Comprobante/Conceptos/Concepto/Parte
ELEM  /Comprobante/Conceptos/Concepto/Parte/InformacionAduanera
attr  /Comprobante/Conceptos/Concepto/Parte/InformacionAduanera@NumeroPedimento [REQ]
attr  /Comprobante/Conceptos/Concepto/Parte@ClaveProdServ [REQ]
attr  /Comprobante/Conceptos/Concepto/Parte@NoIdentificacion [opt]
attr  /Comprobante/Conceptos/Concepto/Parte@Cantidad [REQ]
attr  /Comprobante/Conceptos/Concepto/Parte@Unidad [opt]
attr  /Comprobante/Conceptos/Concepto/Parte@Descripcion [REQ]
attr  /Comprobante/Conceptos/Concepto/Parte@ValorUnitario [opt]
attr  /Comprobante/Conceptos/Concepto/Parte@Importe [opt]
attr  /Comprobante/Conceptos/Concepto@ClaveProdServ [REQ]
attr  /Comprobante/Conceptos/Concepto@NoIdentificacion [opt]
attr  /Comprobante/Conceptos/Concepto@Cantidad [REQ]
attr  /Comprobante/Conceptos/Concepto@ClaveUnidad [REQ]
attr  /Comprobante/Conceptos/Concepto@Unidad [opt]
attr  /Comprobante/Conceptos/Concepto@Descripcion [REQ]
attr  /Comprobante/Conceptos/Concepto@ValorUnitario [REQ]
attr  /Comprobante/Conceptos/Concepto@Importe [REQ]
attr  /Comprobante/Conceptos/Concepto@Descuento [opt]
attr  /Comprobante/Conceptos/Concepto@ObjetoImp [REQ]
ELEM  /Comprobante/Impuestos
ELEM  /Comprobante/Impuestos/Retenciones
ELEM  /Comprobante/Impuestos/Retenciones/Retencion
attr  /Comprobante/Impuestos/Retenciones/Retencion@Impuesto [REQ]
attr  /Comprobante/Impuestos/Retenciones/Retencion@Importe [REQ]
ELEM  /Comprobante/Impuestos/Traslados
ELEM  /Comprobante/Impuestos/Traslados/Traslado
attr  /Comprobante/Impuestos/Traslados/Traslado@Base [REQ]
attr  /Comprobante/Impuestos/Traslados/Traslado@Impuesto [REQ]
attr  /Comprobante/Impuestos/Traslados/Traslado@TipoFactor [REQ]
attr  /Comprobante/Impuestos/Traslados/Traslado@TasaOCuota [opt]
attr  /Comprobante/Impuestos/Traslados/Traslado@Importe [opt]
attr  /Comprobante/Impuestos@TotalImpuestosRetenidos [opt]
attr  /Comprobante/Impuestos@TotalImpuestosTrasladados [opt]
ELEM  /Comprobante/Complemento
ELEM  /Comprobante/Addenda
attr  /Comprobante@Version [REQ]
attr  /Comprobante@Serie [opt]
attr  /Comprobante@Folio [opt]
attr  /Comprobante@Fecha [REQ]
attr  /Comprobante@Sello [REQ]
attr  /Comprobante@FormaPago [opt]
attr  /Comprobante@NoCertificado [REQ]
attr  /Comprobante@Certificado [REQ]
attr  /Comprobante@CondicionesDePago [opt]
attr  /Comprobante@SubTotal [REQ]
attr  /Comprobante@Descuento [opt]
attr  /Comprobante@Moneda [REQ]
attr  /Comprobante@TipoCambio [opt]
attr  /Comprobante@Total [REQ]
attr  /Comprobante@TipoDeComprobante [REQ]
attr  /Comprobante@Exportacion [REQ]
attr  /Comprobante@MetodoPago [opt]
attr  /Comprobante@LugarExpedicion [REQ]
attr  /Comprobante@Confirmacion [opt]
```

## Complemento Nómina 1.2 (`docs/nomina12.xsd`)

```
ELEM  /Nomina
ELEM  /Nomina/Emisor
ELEM  /Nomina/Emisor/EntidadSNCF
attr  /Nomina/Emisor/EntidadSNCF@OrigenRecurso [REQ]
attr  /Nomina/Emisor/EntidadSNCF@MontoRecursoPropio [opt]
attr  /Nomina/Emisor@Curp [opt]
attr  /Nomina/Emisor@RegistroPatronal [opt]
attr  /Nomina/Emisor@RfcPatronOrigen [opt]
ELEM  /Nomina/Receptor
ELEM  /Nomina/Receptor/SubContratacion
attr  /Nomina/Receptor/SubContratacion@RfcLabora [REQ]
attr  /Nomina/Receptor/SubContratacion@PorcentajeTiempo [REQ]
attr  /Nomina/Receptor@Curp [REQ]
attr  /Nomina/Receptor@NumSeguridadSocial [opt]
attr  /Nomina/Receptor@FechaInicioRelLaboral [opt]
attr  /Nomina/Receptor@Antigüedad [opt]
attr  /Nomina/Receptor@TipoContrato [REQ]
attr  /Nomina/Receptor@Sindicalizado [opt]
attr  /Nomina/Receptor@TipoJornada [opt]
attr  /Nomina/Receptor@TipoRegimen [REQ]
attr  /Nomina/Receptor@NumEmpleado [REQ]
attr  /Nomina/Receptor@Departamento [opt]
attr  /Nomina/Receptor@Puesto [opt]
attr  /Nomina/Receptor@RiesgoPuesto [opt]
attr  /Nomina/Receptor@PeriodicidadPago [REQ]
attr  /Nomina/Receptor@Banco [opt]
attr  /Nomina/Receptor@CuentaBancaria [opt]
attr  /Nomina/Receptor@SalarioBaseCotApor [opt]
attr  /Nomina/Receptor@SalarioDiarioIntegrado [opt]
attr  /Nomina/Receptor@ClaveEntFed [REQ]
ELEM  /Nomina/Percepciones
ELEM  /Nomina/Percepciones/Percepcion
ELEM  /Nomina/Percepciones/Percepcion/AccionesOTitulos
attr  /Nomina/Percepciones/Percepcion/AccionesOTitulos@ValorMercado [REQ]
attr  /Nomina/Percepciones/Percepcion/AccionesOTitulos@PrecioAlOtorgarse [REQ]
ELEM  /Nomina/Percepciones/Percepcion/HorasExtra
attr  /Nomina/Percepciones/Percepcion/HorasExtra@Dias [REQ]
attr  /Nomina/Percepciones/Percepcion/HorasExtra@TipoHoras [REQ]
attr  /Nomina/Percepciones/Percepcion/HorasExtra@HorasExtra [REQ]
attr  /Nomina/Percepciones/Percepcion/HorasExtra@ImportePagado [REQ]
attr  /Nomina/Percepciones/Percepcion@TipoPercepcion [REQ]
attr  /Nomina/Percepciones/Percepcion@Clave [REQ]
attr  /Nomina/Percepciones/Percepcion@Concepto [REQ]
attr  /Nomina/Percepciones/Percepcion@ImporteGravado [REQ]
attr  /Nomina/Percepciones/Percepcion@ImporteExento [REQ]
ELEM  /Nomina/Percepciones/JubilacionPensionRetiro
attr  /Nomina/Percepciones/JubilacionPensionRetiro@TotalUnaExhibicion [opt]
attr  /Nomina/Percepciones/JubilacionPensionRetiro@TotalParcialidad [opt]
attr  /Nomina/Percepciones/JubilacionPensionRetiro@MontoDiario [opt]
attr  /Nomina/Percepciones/JubilacionPensionRetiro@IngresoAcumulable [REQ]
attr  /Nomina/Percepciones/JubilacionPensionRetiro@IngresoNoAcumulable [REQ]
ELEM  /Nomina/Percepciones/SeparacionIndemnizacion
attr  /Nomina/Percepciones/SeparacionIndemnizacion@TotalPagado [REQ]
attr  /Nomina/Percepciones/SeparacionIndemnizacion@NumAñosServicio [REQ]
attr  /Nomina/Percepciones/SeparacionIndemnizacion@UltimoSueldoMensOrd [REQ]
attr  /Nomina/Percepciones/SeparacionIndemnizacion@IngresoAcumulable [REQ]
attr  /Nomina/Percepciones/SeparacionIndemnizacion@IngresoNoAcumulable [REQ]
attr  /Nomina/Percepciones@TotalSueldos [opt]
attr  /Nomina/Percepciones@TotalSeparacionIndemnizacion [opt]
attr  /Nomina/Percepciones@TotalJubilacionPensionRetiro [opt]
attr  /Nomina/Percepciones@TotalGravado [REQ]
attr  /Nomina/Percepciones@TotalExento [REQ]
ELEM  /Nomina/Deducciones
ELEM  /Nomina/Deducciones/Deduccion
attr  /Nomina/Deducciones/Deduccion@TipoDeduccion [REQ]
attr  /Nomina/Deducciones/Deduccion@Clave [REQ]
attr  /Nomina/Deducciones/Deduccion@Concepto [REQ]
attr  /Nomina/Deducciones/Deduccion@Importe [REQ]
attr  /Nomina/Deducciones@TotalOtrasDeducciones [opt]
attr  /Nomina/Deducciones@TotalImpuestosRetenidos [opt]
ELEM  /Nomina/OtrosPagos
ELEM  /Nomina/OtrosPagos/OtroPago
ELEM  /Nomina/OtrosPagos/OtroPago/SubsidioAlEmpleo
attr  /Nomina/OtrosPagos/OtroPago/SubsidioAlEmpleo@SubsidioCausado [REQ]
ELEM  /Nomina/OtrosPagos/OtroPago/CompensacionSaldosAFavor
attr  /Nomina/OtrosPagos/OtroPago/CompensacionSaldosAFavor@SaldoAFavor [REQ]
attr  /Nomina/OtrosPagos/OtroPago/CompensacionSaldosAFavor@Año [REQ]
attr  /Nomina/OtrosPagos/OtroPago/CompensacionSaldosAFavor@RemanenteSalFav [REQ]
attr  /Nomina/OtrosPagos/OtroPago@TipoOtroPago [REQ]
attr  /Nomina/OtrosPagos/OtroPago@Clave [REQ]
attr  /Nomina/OtrosPagos/OtroPago@Concepto [REQ]
attr  /Nomina/OtrosPagos/OtroPago@Importe [REQ]
ELEM  /Nomina/Incapacidades
ELEM  /Nomina/Incapacidades/Incapacidad
attr  /Nomina/Incapacidades/Incapacidad@DiasIncapacidad [REQ]
attr  /Nomina/Incapacidades/Incapacidad@TipoIncapacidad [REQ]
attr  /Nomina/Incapacidades/Incapacidad@ImporteMonetario [opt]
attr  /Nomina@Version [REQ]
attr  /Nomina@TipoNomina [REQ]
attr  /Nomina@FechaPago [REQ]
attr  /Nomina@FechaInicialPago [REQ]
attr  /Nomina@FechaFinalPago [REQ]
attr  /Nomina@NumDiasPagados [REQ]
attr  /Nomina@TotalPercepciones [opt]
attr  /Nomina@TotalDeducciones [opt]
attr  /Nomina@TotalOtrosPagos [opt]
```

## Complemento Recepción de Pagos 2.0 (`docs/pagos20.xsd`)

```
ELEM  /Pagos
ELEM  /Pagos/Totales
attr  /Pagos/Totales@TotalRetencionesIVA [opt]
attr  /Pagos/Totales@TotalRetencionesISR [opt]
attr  /Pagos/Totales@TotalRetencionesIEPS [opt]
attr  /Pagos/Totales@TotalTrasladosBaseIVA16 [opt]
attr  /Pagos/Totales@TotalTrasladosImpuestoIVA16 [opt]
attr  /Pagos/Totales@TotalTrasladosBaseIVA8 [opt]
attr  /Pagos/Totales@TotalTrasladosImpuestoIVA8 [opt]
attr  /Pagos/Totales@TotalTrasladosBaseIVA0 [opt]
attr  /Pagos/Totales@TotalTrasladosImpuestoIVA0 [opt]
attr  /Pagos/Totales@TotalTrasladosBaseIVAExento [opt]
attr  /Pagos/Totales@MontoTotalPagos [REQ]
ELEM  /Pagos/Pago
ELEM  /Pagos/Pago/DoctoRelacionado
ELEM  /Pagos/Pago/DoctoRelacionado/ImpuestosDR
ELEM  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/RetencionesDR
ELEM  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/RetencionesDR/RetencionDR
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/RetencionesDR/RetencionDR@BaseDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/RetencionesDR/RetencionDR@ImpuestoDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/RetencionesDR/RetencionDR@TipoFactorDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/RetencionesDR/RetencionDR@TasaOCuotaDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/RetencionesDR/RetencionDR@ImporteDR [REQ]
ELEM  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/TrasladosDR
ELEM  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/TrasladosDR/TrasladoDR
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/TrasladosDR/TrasladoDR@BaseDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/TrasladosDR/TrasladoDR@ImpuestoDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/TrasladosDR/TrasladoDR@TipoFactorDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/TrasladosDR/TrasladoDR@TasaOCuotaDR [opt]
attr  /Pagos/Pago/DoctoRelacionado/ImpuestosDR/TrasladosDR/TrasladoDR@ImporteDR [opt]
attr  /Pagos/Pago/DoctoRelacionado@IdDocumento [REQ]
attr  /Pagos/Pago/DoctoRelacionado@Serie [opt]
attr  /Pagos/Pago/DoctoRelacionado@Folio [opt]
attr  /Pagos/Pago/DoctoRelacionado@MonedaDR [REQ]
attr  /Pagos/Pago/DoctoRelacionado@EquivalenciaDR [opt]
attr  /Pagos/Pago/DoctoRelacionado@NumParcialidad [REQ]
attr  /Pagos/Pago/DoctoRelacionado@ImpSaldoAnt [REQ]
attr  /Pagos/Pago/DoctoRelacionado@ImpPagado [REQ]
attr  /Pagos/Pago/DoctoRelacionado@ImpSaldoInsoluto [REQ]
attr  /Pagos/Pago/DoctoRelacionado@ObjetoImpDR [REQ]
ELEM  /Pagos/Pago/ImpuestosP
ELEM  /Pagos/Pago/ImpuestosP/RetencionesP
ELEM  /Pagos/Pago/ImpuestosP/RetencionesP/RetencionP
attr  /Pagos/Pago/ImpuestosP/RetencionesP/RetencionP@ImpuestoP [REQ]
attr  /Pagos/Pago/ImpuestosP/RetencionesP/RetencionP@ImporteP [REQ]
ELEM  /Pagos/Pago/ImpuestosP/TrasladosP
ELEM  /Pagos/Pago/ImpuestosP/TrasladosP/TrasladoP
attr  /Pagos/Pago/ImpuestosP/TrasladosP/TrasladoP@BaseP [REQ]
attr  /Pagos/Pago/ImpuestosP/TrasladosP/TrasladoP@ImpuestoP [REQ]
attr  /Pagos/Pago/ImpuestosP/TrasladosP/TrasladoP@TipoFactorP [REQ]
attr  /Pagos/Pago/ImpuestosP/TrasladosP/TrasladoP@TasaOCuotaP [opt]
attr  /Pagos/Pago/ImpuestosP/TrasladosP/TrasladoP@ImporteP [opt]
attr  /Pagos/Pago@FechaPago [REQ]
attr  /Pagos/Pago@FormaDePagoP [REQ]
attr  /Pagos/Pago@MonedaP [REQ]
attr  /Pagos/Pago@TipoCambioP [opt]
attr  /Pagos/Pago@Monto [REQ]
attr  /Pagos/Pago@NumOperacion [opt]
attr  /Pagos/Pago@RfcEmisorCtaOrd [opt]
attr  /Pagos/Pago@NomBancoOrdExt [opt]
attr  /Pagos/Pago@CtaOrdenante [opt]
attr  /Pagos/Pago@RfcEmisorCtaBen [opt]
attr  /Pagos/Pago@CtaBeneficiario [opt]
attr  /Pagos/Pago@TipoCadPago [opt]
attr  /Pagos/Pago@CertPago [opt]
attr  /Pagos/Pago@CadPago [opt]
attr  /Pagos/Pago@SelloPago [opt]
attr  /Pagos@Version [REQ]
```

## Complemento IEDU (Instituciones Educativas) (`docs/iedu.xsd`)

```
ELEM  /instEducativas
attr  /instEducativas@version [REQ]
attr  /instEducativas@nombreAlumno [REQ]
attr  /instEducativas@CURP [REQ]
attr  /instEducativas@nivelEducativo [REQ]
attr  /instEducativas@autRVOE [REQ]
attr  /instEducativas@rfcPago [opt]
```

## Complemento Impuestos Locales (`docs/implocal.xsd`)

```
ELEM  /ImpuestosLocales
ELEM  /ImpuestosLocales/RetencionesLocales
attr  /ImpuestosLocales/RetencionesLocales@ImpLocRetenido [REQ]
attr  /ImpuestosLocales/RetencionesLocales@TasadeRetencion [REQ]
attr  /ImpuestosLocales/RetencionesLocales@Importe [REQ]
ELEM  /ImpuestosLocales/TrasladosLocales
attr  /ImpuestosLocales/TrasladosLocales@ImpLocTrasladado [REQ]
attr  /ImpuestosLocales/TrasladosLocales@TasadeTraslado [REQ]
attr  /ImpuestosLocales/TrasladosLocales@Importe [REQ]
attr  /ImpuestosLocales@version [REQ]
attr  /ImpuestosLocales@TotaldeRetenciones [REQ]
attr  /ImpuestosLocales@TotaldeTraslados [REQ]
```

## Catálogo c_ClaveProdServ (`docs/catCFDI.xsd`) — familias relevantes

Total de claves oficiales: **52,747**. El XSD trae solo los códigos
(SIN descripciones); la semántica de familia viene de la jerarquía UNSPSC
(segmento 15 = combustibles/lubricantes; 8612 = servicios educativos).
Para descripciones individuales se necesitaría el `catCFDI.xls` (opcional).

### Familia 1510 — Combustibles (35 claves oficiales)

```
15101500, 15101502, 15101503, 15101504, 15101505, 15101506, 15101507, 15101508, 15101509, 15101510, 15101511, 15101512, 15101513, 15101514, 15101515, 15101600, 15101601, 15101602, 15101603, 15101604, 15101605, 15101606, 15101607, 15101608, 15101609, 15101610, 15101611, 15101612, 15101613, 15101614, 15101700, 15101701, 15101702, 15101800, 15101801
```

⚠️ La clave `15101501` (hardcodeada hoy en `constants.py`) NO existe en el
catálogo oficial — es una clave muerta. El diesel (`15101505`) y 30 claves
más de esta familia NO están en la lista hardcodeada actual.

### Familia 8612 — Servicios educativos (15 claves oficiales)

```
86121500, 86121501, 86121502, 86121503, 86121504, 86121600, 86121601, 86121602, 86121700, 86121701, 86121702, 86121800, 86121802, 86121803, 86121804
```
