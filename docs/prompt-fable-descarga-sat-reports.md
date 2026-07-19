# Prompt para Fable — Diseño de "Descargar del SAT" + Vista Reports (árbol global de RFCs)

> Versión: 2026-07-12
> Destinatario: Fable 5 (fase de análisis/arquitectura, NO construcción). Si Fable no está disponible, usar Opus 4.8 con el mismo prompt.
> Esfuerzo recomendado: medium.
> Contexto: CFDI-app, botón "Descargar…" (hoy gris, placeholder) de la barra lateral de bóveda (Task B3) + nueva vista "Reports" separada.

---

## ROL Y CONTEXTO

Eres el modelo de DISEÑO (fase de análisis/arquitectura) de **CFDI-app**, una app de escritorio Python (PySide6, NO PyQt6 por licencia LGPL) para contadores mexicanos que procesa CFDIs (facturas, nómina, pagos) del SAT. El dueño (Svei) es contador mexicano, desarrollador solo, hispanohablante. Trabaja por fases: primero diseño documentado (tú), después construcción (Sonnet 5 u Opus 4.8, sobre ese diseño). **NO vas a escribir código Python en esta conversación** — tu entregable es un documento de diseño, al estilo de las secciones existentes en `ROADMAP.md` (con tablas de decisiones D-número, con fecha y razón).

Lee primero `PROMPT.md` y `ROADMAP.md` completos (te los pega/adjunta Svei) antes de responder nada. Presta atención especial a:
- **§5.3** — nota de diseño a futuro: evolución a shell/dashboard (la vista "Reports" de este prompt es la primera pieza real de esa evolución).
- **§10, punto 6** — el registro exacto de por qué esta tarea se te asignó a ti en vez de construirse directo en la sesión de B3.
- **D21** (filtro por periodo, jerarquía dura RFC→dirección, JAMÁS mezclar RFCs en un resultado) y **D11** (nunca eliminar funcionalidad existente sin consultar antes).
- `docs/design-f2.8-combustible-fix-y-ux.md`, sección **Task B3**, especialmente el bloque "CONSTRUIDO 2026-07-12" al final — ahí está exactamente qué se construyó y qué decisiones tomó Svei sobre el modelo de árbol/casillas.

### Proyecto EN alcance

**Solo CFDI-app.** Ubicación del repo: donde Svei te lo indique (créelo desde el registro de proyectos si trabajas con memoria persistente — nombre del proyecto es `cfdi-app`).

### Proyectos explícitamente FUERA de alcance

- **importar_xml_a_contabilidad** — app independiente (Tkinter, no PySide6). Ningún código ni arquitectura se comparte con CFDI-app. No asumas nada de ese proyecto.
- **CFDI_Renamer** — app independiente de renombrado de PDF+XML de nómina. Sin relación de código.
- **papeles-trabajo** — Excel de 18 hojas, proyecto separado con su propio `CLAUDE.md`. Sin relación de código con CFDI-app (aunque ambos son "fiscales", NO comparten codebase).

### Pieza posiblemente relacionada — PREGUNTAR, NO ASUMIR

Existe un proyecto separado, **`herramienta-fiscal-automation`** (sin nombre final aún), que YA tiene **arquitectura de descarga SAT completada** (Python + Playwright, autenticación CIEC primero y e.firma después, con contraseña NUNCA persistida — modelo tipo CONTPAQi). También existe una **extensión de Chrome funcional que resuelve CAPTCHAs de www.sat.gob.mx**, pensada como componente reutilizable de esa herramienta.

**El registro de proyectos de Svei NO declara una relación de código explícita entre CFDI-app y `herramienta-fiscal-automation`.** Antes de diseñar la lógica de autenticación/descarga de este prompt desde cero, **pregúntale a Svei directamente**:

1. ¿La descarga del SAT en CFDI-app debe **reutilizar** la arquitectura ya diseñada en `herramienta-fiscal-automation` (mismo patrón CIEC→e.firma, misma extensión de CAPTCHA), o son sistemas independientes por diseño (uno es descarga bajo demanda desde la GUI, el otro es automatización programada multi-RFC)?
2. Si se reutiliza: ¿es una dependencia compartida, una librería común, o simplemente "mismo patrón, código separado"?
3. Si Svei no tiene ese proyecto a la mano en esta sesión, dilo como supuesto abierto y diseña la interfaz de autenticación de forma que sea fácil de sustituir después (no la acoples al flujo de descarga+categorización).

**No dupliques trabajo de diseño de autenticación ya hecho** si Svei confirma que debe reutilizarse — en ese caso tu entregable se enfoca en la parte NUEVA: qué pasa con los XMLs DESPUÉS de que llegan (auto-categorización) y la vista Reports.

## RESTRICCIÓN DURA — REGLAS YA VIGENTES QUE NO SE TOCAN

- **D21** (`ROADMAP.md`): jerarquía dura RFC→Emitidas/Recibidas. Ningún resultado, tabla o vista puede mezclar dos RFCs. La vista Reports (árbol global) **muestra** todos los RFCs pero cualquier acción sobre datos (abrir, cargar, reportar) sigue obedeciendo esta regla — es un directorio/mapa, no una tabla combinada.
- **D11**: eliminar funcionalidad existente y funcionando requiere consultar a Svei antes, con pros/contras — no solo avisar después.
- **Reglas anti-Bug-1** (`ROADMAP.md` §6.2): ningún slot conectado a señales de un hilo/worker puede abrir diálogos modales. Cualquier diálogo nace de un clic directo del usuario.
- **La ruta de la bóveda es CONFIGURABLE** (decisión D39, 2026-07-13, ver `docs/design-b3-r2-caratula-y-boveda.md`): la fuente de verdad es `settings.get_vault_root()`, con default `Documents\CFDI-Processor\BovedaCFDI`, y existe "Cambiar ubicación de bóveda…" que muda la bóveda completa. Tu diseño de descarga+auto-categorización NUNCA debe asumir una ruta fija — siempre la ruta activa de settings.
- **`cfdi_app/vault.py`** ya existe (construido en B3): interfaz `VaultSource` + implementación `FolderVaultSource` que enumera `BovedaCFDI/{RFC}/{Emitidas|Recibidas}/{YYYY}/{MM}`. Tu diseño de auto-categorización y de la vista Reports **debe apoyarse en esa interfaz existente**, no proponer una paralela. Si concluyes que `VaultSource` necesita un método nuevo (p. ej. "todas las carpetas con al menos un archivo, sin importar selección"), dilo explícitamente como una extensión propuesta, no una reescritura.
- **Modelo de árbol de B3**: la barra lateral de carga (Task B3, ya construida) usa un árbol único con TODOS los RFCs visibles y casillas — es el árbol para **elegir qué procesar**. La vista Reports de este prompt es **distinta en propósito** (ver/navegar el estado completo de la bóveda, no seleccionar una carga), aunque puede reutilizar componentes visuales. No los fusiones sin preguntar primero si Svei quiere que sean la misma pantalla o dos pantallas separadas.

## OBJETIVO DE ESTA FASE

Diseñar (no construir) dos piezas relacionadas que Svei pidió durante el diseño de B3:

1. **Flujo "Descargar del SAT"**: hoy es un botón gris (placeholder) en la barra lateral de bóveda y una entrada de menú deshabilitada ("Bóveda → Descargar del SAT…"). El flujo real debe:
   - Autenticar contra el SAT (CIEC primero; e.firma después — ver sección de arriba sobre reutilizar `herramienta-fiscal-automation`).
   - Descargar los XMLs correspondientes.
   - **Auto-categorizarlos** en la estructura de carpetas existente `BovedaCFDI/{RFC}/{Emitidas|Recibidas}/{YYYY}/{MM}` sin intervención manual del usuario (el sistema ya sabe el RFC, la dirección y la fecha de cada XML descargado — mismo criterio que usa `core.determine_file_naming_components` para nombrar archivos, pero aplicado a dónde SE GUARDA el archivo, no a cómo se nombra el reporte).

2. **Vista "Reports"**: una pantalla (o panel) separada que muestra el **árbol de TODOS los RFCs que existen en la bóveda**, para que Svei pueda ver de un vistazo qué tiene archivado sin tener que abrir el árbol de carga de B3. Evalúa si debe mostrar solo estructura (RFC/dirección/año/mes) o también conteos (cuántos XMLs por mes) — pregunta a Svei su preferencia, no la asumas.

## FUENTE DE LA VERDAD: TÚ NO LA TIENES COMPLETA

Igual que en diseños anteriores de este proyecto, **tu primera respuesta NO debe ser un diseño** — debe ser una **entrevista estructurada, por rondas**, priorizando las preguntas de mayor ambigüedad/impacto primero.

**Preguntas concretas a hacer a Svei** (ajusta y agrega las que hagan falta):

- La pregunta de reutilización de `herramienta-fiscal-automation` (arriba) — es la de mayor impacto arquitectónico, hazla primero.
- ¿"Descargar del SAT" descarga TODO lo disponible para un RFC, o Svei quiere elegir un rango de fechas/tipo antes de descargar (como ya existe en el portal del SAT)?
- ¿Qué pasa si un XML descargado ya existe en la bóveda (mismo UUID)? ¿Se ignora, se sobrescribe, se avisa? (Nota: sin bóveda SQLite todavía — F4 — la detección de duplicados por UUID hoy solo puede hacerse comparando XMLs ya en disco, no con índice; sé honesto sobre esa limitación si aplica.)
- ¿La vista Reports reemplaza la barra lateral de B3, vive al lado, o es una pestaña/ventana distinta? Dale tu opinión de UX pero pregunta antes de decidir — Svei ya mencionó explícitamente que "Reports" es donde se vería el árbol completo, distinto del árbol de selección de carga.
- ¿Reports debe mostrar RFCs sin ningún XML todavía (carpeta vacía creada pero sin contenido), o solo los que tienen datos?
- ¿Es una función de todas las ediciones (Lite/Pro/Top) o exclusiva de alguna, igual que se preguntó para el Reporte Fiscal Pro? (Ver `ROADMAP.md` D10 — Svei ya tiene ese patrón de pregunta establecido para features nuevas.)
- Autenticación: ¿dónde se guardan las credenciales CIEC de cada RFC (si se guardan)? Sigue el modelo "contraseña nunca persistida" que Svei ya usa en `herramienta-fiscal-automation` — pregúntale si aplica igual aquí o si CFDI-app pide la contraseña cada vez.
- ¿La descarga corre en un hilo aparte como el procesamiento actual (patrón QThread de `ROADMAP.md` §6.3), con barra de progreso? Asume que sí salvo que Svei diga lo contrario — es el patrón establecido en toda la app.
- Manejo de errores de red/CAPTCHA/sesión expirada durante la descarga: ¿reintentos automáticos (como en `herramienta-fiscal-automation`, jitter 15–30 min) o falla inmediata con mensaje claro al usuario (más simple, más apropiado para un flujo interactivo bajo demanda vs. uno programado)?

**Solo después de tener las respuestas** (puede requerir varias rondas), produce el documento de diseño.

## ENTREGABLE ESPERADO (tras la entrevista)

Un documento en el mismo estilo que las secciones ya existentes en `ROADMAP.md` (para copiar/pegar como nueva sección, ej. futura §18, o extensión de §10 punto 6):

1. **Objetivo de cada pieza** (Descargar + Reports), en una frase cada una.

2. **Relación con `herramienta-fiscal-automation`**, resuelta explícitamente (reutiliza / independiente / pendiente).

3. **Flujo de autenticación y descarga**, paso a paso, en español llano (NO código) — incluyendo qué hilo/worker lo ejecuta y qué feedback ve el usuario.

4. **Regla de auto-categorización**: cómo se determina RFC/dirección/año/mes de cada XML descargado y se decide su carpeta destino, apoyándose en `vault.py` existente.

5. **Diseño de la vista Reports**: dónde vive en la ventana (panel, pestaña, ventana nueva), qué muestra exactamente, cómo se diferencia del árbol de carga de B3.

6. **Manejo de duplicados y errores**, con los límites honestos de lo que es posible sin F4 (bóveda SQLite) si aplica.

7. **Extensiones propuestas a `cfdi_app/vault.py`** (si las hay), como lista de métodos nuevos con su propósito — sin implementarlos.

8. **Tabla de decisiones** (estilo D-número, continuando la numeración de `ROADMAP.md`) para las que se cierren en esta conversación, con fecha y razón.

9. **Preguntas que quedaron abiertas / pendientes de confirmar con Svei.**

10. **Nota explícita de qué construcción NO se cubre hoy** (para que Sonnet/Opus, en la fase siguiente, no invente alcance) — en particular, deja claro que esta pieza depende de F6 (validación de estatus SAT, según roadmap) solo si aplica, o corrige esa dependencia si tu análisis concluye que no es necesaria para el flujo de descarga básico.

**No propongas nombres de archivos, clases ni funciones Python** — eso es trabajo de la fase de construcción.

---

## ESTILO DE CÓDIGO (referencia para cuando esto pase a construcción — Sonnet 5 u Opus 4.8)

Aunque tú no escribes código en esta fase, tu documento de diseño debe ser construible respetando estas reglas — no propongas una arquitectura que las viole:

- Funciones pequeñas de propósito único.
- Comentarios explicativos estilo "profesor de salón de clases" — el código debe poder debuggearse en una sesión fresca de IA sin contexto previo.
- Nombres en lenguaje natural, descriptivos.
- Prohibidos los patrones ingeniosos-pero-crípticos.
- Archivos chicos, arquitectura modular, separación de responsabilidades (SRP).
- Carpetas: lowercase kebab-case. Python: snake_case. Sin espacios, acentos ni caracteres especiales en nombres de archivos.

## GIT (referencia para la fase de construcción)

Rama por fase; probar local antes de merge a main; deploy solo desde main (cuando aplique). Si tu diseño toca código que ya tiene tag de respaldo (D20), la fase de construcción deberá crear un tag nuevo antes de tocar `vault.py` o `main_window.py`, siguiendo el mismo criterio que D20.

---

## Fin del prompt

Cópialo tal cual (desde "ROL Y CONTEXTO") y pégalo en Fable junto con `PROMPT.md`, `ROADMAP.md` y `docs/design-f2.8-combustible-fix-y-ux.md` del repo. El modelo debería arrancar con la entrevista, empezando por la pregunta de reutilización de `herramienta-fiscal-automation`.
