# Requerimientos

Es una aplicación de escritorio diseñada para automatizar la extracción de comprobantes de compras y ventas.

El sistema permite procesar comprobantes en formato PDF, JPG y PNG, extraer automáticamente la información mediante OCR y lectura de documentos, clasificar cada comprobante utilizando un modelo local de Ollama y almacenar toda la información en PostgreSQL para su posterior consulta y exportación a Excel.

Todo el procesamiento se realiza localmente, garantizando la privacidad de la información y eliminando la dependencia de servicios en la nube.

---

## REQ-1: Selección de comprobantes

### Historia de usuario:

Como contador

quiero seleccionar uno o varios comprobantes desde mi computadora

para iniciar el procesamiento automático.

### Feature name:

```text
feature/HU01-select-documents
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN el contador selecciona uno o varios archivos compatibles

THEN SYSTEM SHALL mostrar la lista de archivos listos para procesar.

#### R2

---

WHEN el contador selecciona un archivo con formato no soportado

THEN SYSTEM SHALL mostrar un mensaje indicando que el archivo no puede procesarse.

#### R3

---

WHEN el contador no selecciona ningún archivo

THEN SYSTEM SHALL impedir iniciar el procesamiento.

---

## REQ-2: Procesamiento por lote

### Historia de usuario:

Como contador

quiero procesar varios comprobantes en una sola ejecución

para reducir el tiempo de digitación manual.

### Feature name:

```text
feature/HU02-batch-processing
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN el contador inicia el procesamiento

THEN SYSTEM SHALL procesar todos los archivos seleccionados.

#### R2

---

WHEN ocurre un error durante el procesamiento de un comprobante

THEN SYSTEM SHALL registrar el error y continuar procesando los demás archivos.

#### R3

---

WHEN finaliza el procesamiento

THEN SYSTEM SHALL mostrar un resumen con la cantidad de comprobantes procesados, errores y tiempo total.

---

## REQ-3: Extracción de texto

### Historia de usuario:

Como contador

quiero que el sistema extraiga automáticamente el texto de los comprobantes

para evitar ingresar la información manualmente.

### Feature name:

```text
feature/HU03-text-extraction
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN el comprobante corresponde a un PDF con texto digital

THEN SYSTEM SHALL extraer el contenido sin utilizar OCR.

#### R2

---

WHEN el comprobante corresponde a una imagen o un PDF escaneado

THEN SYSTEM SHALL utilizar RapidOCR para obtener el texto.

#### R3

---

WHEN RapidOCR no pueda extraer el texto

THEN SYSTEM SHALL registrar el comprobante como error.

---

## REQ-4: Extracción de información

### Historia de usuario:

Como contador

quiero que el sistema identifique automáticamente la información del comprobante

para almacenarla sin intervención manual.

### Feature name:

```text
feature/HU04-document-parser
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN el texto haya sido extraído correctamente

THEN SYSTEM SHALL identificar la información tributaria disponible.

#### R2

---

WHEN algún dato no pueda identificarse

THEN SYSTEM SHALL registrar únicamente los datos encontrados.

---

## REQ-5: Clasificación automática

### Historia de usuario:

Como contador

quiero que el sistema clasifique automáticamente los comprobantes

para reducir el tiempo de categorización.

### Feature name:

```text
feature/HU05-ai-classification
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN exista una descripción del comprobante

THEN SYSTEM SHALL enviar únicamente la descripción al modelo Ollama.

#### R2

---

WHEN Ollama responda correctamente

THEN SYSTEM SHALL registrar únicamente el código de la categoría.

#### R3

---

WHEN Ollama no pueda determinar una categoría

THEN SYSTEM SHALL dejar la categoría sin asignar.

---

## REQ-6: Gestión de categorías

### Historia de usuario:

Como contador

quiero administrar las categorías mediante un archivo YAML

para modificar el catálogo sin cambiar el código.

### Feature name:

```text
feature/HU06-categories
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN la aplicación inicie

THEN SYSTEM SHALL sincronizar automáticamente las categorías del archivo YAML con PostgreSQL.

#### R2

---

WHEN exista una categoría nueva en el archivo YAML

THEN SYSTEM SHALL crearla en la base de datos.

#### R3

---

WHEN una categoría sea eliminada del YAML

THEN SYSTEM SHALL marcarla como inactiva.

---

## REQ-7: Almacenamiento de comprobantes

### Historia de usuario:

Como contador

quiero almacenar todos los comprobantes procesados

para mantener un historial de información.

### Feature name:

```text
feature/HU07-persistence
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN un comprobante haya sido procesado correctamente

THEN SYSTEM SHALL almacenar toda la información en PostgreSQL.

#### R2

---

WHEN el comprobante ya exista según su hash

THEN SYSTEM SHALL evitar almacenarlo nuevamente.

---

## REQ-8: Historial de procesamiento

### Historia de usuario:

Como contador

quiero consultar el historial de procesamiento

para conocer el resultado de cada ejecución.

### Feature name:

```text
feature/HU08-processing-history
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN una ejecución finalice

THEN SYSTEM SHALL registrar fecha, duración, cantidad de comprobantes procesados y errores.

#### R2

---

WHEN existan errores

THEN SYSTEM SHALL registrar el estado de la ejecución como FAILED.

---

## REQ-9: Corrección manual

### Historia de usuario:

Como contador

quiero modificar la categoría asignada

para corregir clasificaciones incorrectas.

### Feature name:

```text
feature/HU09-manual-correction
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN el contador cambie una categoría

THEN SYSTEM SHALL registrar la nueva categoría.

#### R2

---

WHEN una categoría sea modificada

THEN SYSTEM SHALL mantener el historial de la corrección.

---

## REQ-10: Exportación a Excel

### Historia de usuario:

Como contador

quiero exportar los comprobantes procesados

para utilizarlos en mis procesos contables.

### Feature name:

```text
feature/HU10-export-excel
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN el contador seleccione un mes

THEN SYSTEM SHALL exportar únicamente los comprobantes correspondientes a dicho período.

#### R2

---

WHEN la exportación finalice

THEN SYSTEM SHALL generar un archivo Excel (.xlsx).

#### R3

---

WHEN el archivo sea generado

THEN SYSTEM SHALL incluir empresa, fecha, serie, número, proveedor, cliente, subtotal, IGV, total, código de categoría y nombre de categoría.

---

## REQ-11: Visualización del procesamiento

### Historia de usuario:

Como contador

quiero visualizar el progreso del procesamiento

para conocer el estado de la ejecución en tiempo real.

### Feature name:

```text
feature/HU11-processing-monitor
```

### Criterios de aceptación (EARS):

#### R1

---

WHEN el procesamiento esté en ejecución

THEN SYSTEM SHALL mostrar el progreso en la interfaz de Streamlit.

#### R2

---

WHEN exista información de seguimiento

THEN SYSTEM SHALL registrar el detalle del procesamiento utilizando Rich en consola.

#### R3

---

WHEN el procesamiento finalice

THEN SYSTEM SHALL mostrar un resumen general de la ejecución.
