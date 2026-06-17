# Privacidad

Este documento describe qué datos manejamos en trama, con quién los compartimos y qué derechos tenés.

trama todavía está en desarrollo. Si algo no te cierra, escribinos antes de subir información sensible.

## Qué datos recolectamos

- **Datos de registro**: email, CUIT, dirección y nombre del nodo (cooperativa, mutual, organización).
- **Archivos que subís**: planillas (xlsx, csv), fotos (jpg, png, heic) o PDFs con tu oferta semanal o lista de pedidos.
- **Datos parseados**: las líneas que extraemos de cada archivo (producto, cantidad, unidad), más la confirmación humana que hacés en pantalla antes de persistir.

## Con quién los compartimos

trama usa un parser híbrido. El camino del archivo depende del formato:

- **xlsx y csv** se procesan **localmente** en nuestro backend. **No** se envían a terceros.
- **Fotos (jpg, png, heic, heif) y PDFs** se envían a **Google Gemini** (API de IA de Google) para extraer el contenido tabular. Esto incluye los bytes completos del archivo: si tu foto tiene anotaciones a mano, precios, firmas o nombres, todo eso viaja a Google junto con la planilla.

Usamos el LLM como **fallback**, no como primera opción. Si podés subir una planilla digital (xlsx, csv) en vez de una foto, evitás el paso por Google.

## Por qué pasamos las fotos por un LLM

Muchxs productorxs trabajan con planillas en cuaderno, fotos de WhatsApp o PDFs escaneados. Forzar a digitalizar antes de usar trama dejaría afuera justo a las personas que más necesitan la herramienta. El LLM es lo que permite que esos formatos también funcionen.

## Qué guarda Google

Google Gemini se rige por sus propios términos para el uso de la API. Recomendamos leer:

- [Términos de servicio de Gemini API](https://ai.google.dev/gemini-api/terms)

En particular, los términos describen si Google retiene los archivos, por cuánto tiempo y bajo qué condiciones puede usarlos para mejorar el modelo. Esos términos pueden cambiar y no dependen de trama.

## Qué guarda trama

- **El archivo crudo** que subiste, en almacenamiento local del backend.
- **El texto parseado** por el deterministic parser o por el LLM, incluyendo la transcripción cruda de cada fila (`parse_attempt.payload`). Esto puede incluir precios o anotaciones que estaban en la planilla original.
- **Tu confirmación humana** sobre las líneas finales antes de persistir.

trama **nunca vende datos a terceros**. No los exponemos en logs públicos, endpoints abiertos ni mensajes de error.

Los precios y montos individuales (`amount_money`) se guardan en `null` por defecto. Cualquier opt-in para activarlos requiere acuerdo explícito del colectivo dueño de los datos.

## Tus derechos

Podés pedirnos:

- Eliminar tu cuenta y todos los datos asociados (archivos, parseos, operaciones).
- Exportar lo que tenemos sobre tu nodo.
- Corregir cualquier dato mal cargado.

Para cualquiera de estos pedidos, escribinos a **ai@lawal.com.ar**.

## Cambios a esta política

Si cambia el flujo de datos, actualizamos este documento y avisamos en la pantalla de carga.
