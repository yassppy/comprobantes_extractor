# 🧾 app de extración de comprobantes

> 📅 **Desarrollo:** 02/08/2026 — 05/08/2026

Un contador que maneja varias empresas recibe decenas de comprobantes cada mes — facturas en PDF, boletas escaneadas, tickets en foto — y tiene que abrirlos uno por uno, copiar los datos al sistema contable externo y clasificar cada gasto manualmente. Eso es horas de trabajo repetitivo que no agrega valor.

Esta app resuelve ese problema: el contador arrastra sus comprobantes, presiona un botón y el sistema extrae la información automáticamente, la clasifica por categoría contable y la deja lista para exportar a Excel. Todo corre en su propia computadora, sin subir documentos a ningún servidor externo.

---

## ✨ Características principales

| Módulo | Descripción |
|---|---|
| 📄 **Extracción** | PDFs con texto digital via `pdfplumber` · Imágenes y PDFs escaneados via `RapidOCR` |
| 🔍 **Parser** | Identificación automática de RUC, serie, número, fechas, montos, moneda y descripción |
| 🤖 **Clasificación IA** | Categorización automática por lotes usando un LLM local (LM Studio / Ollama) |
| ✅ **Validación SUNAT** | Consulta de RUC y DNI de empresas y socios contra SUNAT usando Playwright |
| 💾 **Persistencia** | Almacenamiento en PostgreSQL con deduplicación por hash SHA-256 |
| 📊 **Exportación** | Generación de reportes `.xlsx` por período, empresa y tipo de comprobante |
| 🖥️ **Interfaz** | Panel web con Streamlit · Logs detallados en consola con Rich |

---

## 📸 Capturas de pantalla

### Procesamiento y consulta de comprobantes
![Procesamiento y consulta](assets/app_procesar_consultar_comprobantes.png)

### Consulta, filtros y exportación a Excel
![Consulta y exportación](assets/app_consultar_exportar_comprobantes.png)

### Clasificación automática por lotes con LLM local
![Clasificación de categorías](assets/clasificacion-de-categoria.png)

### Extracción OCR — comprobante de compras (imagen)
![OCR compras](assets/test_compras_ocr.png)

### Extracción PDF — comprobante de ventas
![PDF ventas](assets/test_ventas_pdf.png)

### Validación de RUC contra SUNAT con Playwright
![Validar RUC SUNAT](assets/validar_ruc_sunat.png)

---

## 🏗️ Arquitectura

```
comprobantes_extractor/
├── resources/
│   ├── categories.yaml       # Catálogo de categorías contables (editable sin tocar código)
│   └── settings.yaml
├── src/
│   ├── domain/               # Entidades y enumeraciones del dominio
│   ├── infrastructure/
│   │   ├── extractor/        # pdfplumber + RapidOCR
│   │   ├── parser/           # Parseo de campos tributarios
│   │   ├── scanner/          # Detección de tipo de archivo
│   │   └── sunat/            # Scraping SUNAT con Playwright
│   ├── use_cases/            # Lógica de negocio (process_batch, save_batch, classify_batch, sync_categories…)
│   ├── Persistence/          # Conexión PostgreSQL y repositorios
│   ├── utils/                # Exportador Excel, hash SHA-256, reportes de prueba
│   ├── console/              # Visualización Rich en terminal
│   └── ui/                   # Interfaz Streamlit (componentes y estado)
└── docs/
    ├── database/db.sql       # Esquema PostgreSQL completo
    └── spec/requirements.md  # Requerimientos funcionales
```

---

## ⚙️ Requisitos

- Python **3.13+**
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias)
- PostgreSQL **16+**
- [LM Studio](https://lmstudio.ai/) con modelo `Qwen2.5-1.5B-Instruct Q4_K_M` *(recomendado para 4 GB RAM)*
  > También compatible con Ollama local o en red (ej. Termux en Android).

---

## 🚀 Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/comprobantes_extractor.git
cd comprobantes_extractor/src

# 2. Instalar dependencias
uv sync

# 3. Instalar navegadores Playwright (para validación SUNAT)
uv run playwright install chromium

# 4. Configurar variables de entorno
cp .env.template .env
# Edita .env con tu DATABASE_URL, BASE_URL y MODEL
```

### Configurar `.env`

```dotenv
DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db

# LM Studio (recomendado)
BASE_URL=http://localhost:1234
MODEL=qwen2.5-1.5b-instruct
LLM_BACKEND=lmstudio

# O Ollama local / red
# BASE_URL=http://localhost:11434
# LLM_BACKEND=ollama

LLM_TIMEOUT=120
```

### Crear la base de datos

```sql
-- Ejecutar el esquema completo en tu instancia PostgreSQL
\i docs/database/db.sql
```

---

## ▶️ Ejecutar la aplicación

```bash
cd src

# Sin abrir el navegador automáticamente
uv run streamlit run ui/app.py --server.headless true
```

La app queda disponible en `http://localhost:8501`.

---

## 🗄️ Esquema de base de datos

```
companies           → Empresas del contador (validadas contra SUNAT)
business_partners   → Proveedores y clientes normalizados por documento
categories          → Catálogo sincronizado desde YAML
processing_runs     → Historial de ejecuciones por empresa
documents           → Comprobantes extraídos con todos sus campos
```

---

## 📦 Stack tecnológico

| Capa | Tecnología |
|---|---|
| Interfaz | [Streamlit](https://streamlit.io/) |
| Extracción PDF | [pdfplumber](https://github.com/jsvine/pdfplumber) |
| OCR | [RapidOCR](https://github.com/RapidAI/RapidOCR) |
| Clasificación IA | [LM Studio](https://lmstudio.ai/) / [Ollama](https://ollama.com/) vía HTTP |
| Validación SUNAT | [Playwright](https://playwright.dev/python/) |
| Base de datos | [PostgreSQL 16](https://www.postgresql.org/) + [psycopg3](https://www.psycopg.org/) |
| Exportación | [openpyxl](https://openpyxl.readthedocs.io/) |
| Logs consola | [Rich](https://rich.readthedocs.io/) |
| Gestor de paquetes | [uv](https://docs.astral.sh/uv/) |
