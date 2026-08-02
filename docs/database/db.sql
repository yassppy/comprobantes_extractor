/*
===============================================================================
 Extractor de Comprobantes
 PostgreSQL 16+

 Descripción:
 Base de datos diseñada para una aplicación local que permite:

  - Procesar comprobantes (PDF / JPG / PNG)
  - Extraer información mediante OCR
  - Clasificar automáticamente utilizando Ollama
  - Almacenar el histórico
  - Exportar información mensual a Excel

 Autor: miguel
===============================================================================
*/

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- TABLA: companies
-- ============================================================================
-- Empresas a las que pertenecen los comprobantes.
-- Aunque inicialmente exista una sola empresa, esta tabla permite escalar
-- fácilmente a múltiples clientes del contador.
-- ============================================================================

CREATE TABLE companies (

    id              BIGSERIAL PRIMARY KEY,

    name            VARCHAR(200) NOT NULL,

    ruc             CHAR(11) NOT NULL UNIQUE,

    active          BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE companies IS
'Empresas propietarias de los comprobantes.';



-- ============================================================================
-- TABLA: categories
-- ============================================================================
-- Catálogo sincronizado desde categories.yaml
-- Ollama únicamente devuelve el código de categoría.
-- ============================================================================

CREATE TABLE categories (

    code            VARCHAR(20) PRIMARY KEY,

    name            VARCHAR(150) NOT NULL,

    description     TEXT,

    active          BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE categories IS
'Catálogo de categorías sincronizado desde YAML.';



-- ============================================================================
-- TABLA: processing_runs
-- ============================================================================
-- Cada ejecución representa un lote de procesamiento.
-- Permite conocer estadísticas del procesamiento.
-- ============================================================================

CREATE TABLE processing_runs (

    id                      BIGSERIAL PRIMARY KEY,

    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    finished_at             TIMESTAMPTZ,

    total_files             INTEGER NOT NULL DEFAULT 0,

    processed_files         INTEGER NOT NULL DEFAULT 0,

    failed_files            INTEGER NOT NULL DEFAULT 0,

    duration_seconds        INTEGER,

    status                  VARCHAR(20) NOT NULL
                            CHECK (
                                status IN
                                (
                                    'RUNNING',
                                    'COMPLETED',
                                    'FAILED'
                                )
                            ),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE processing_runs IS
'Historial de ejecuciones del extractor.';



-- ============================================================================
-- TABLA: documents
-- ============================================================================
-- Información principal extraída desde los comprobantes.
-- ============================================================================

CREATE TABLE documents (

    id                      BIGSERIAL PRIMARY KEY,

    processing_run_id       BIGINT NOT NULL
                            REFERENCES processing_runs(id),

    company_id              BIGINT NOT NULL
                            REFERENCES companies(id),

    category_code           VARCHAR(20)
                            REFERENCES categories(code),

    document_type           VARCHAR(20) NOT NULL
                            CHECK (
                                document_type IN
                                (
                                    'SALE',
                                    'PURCHASE'
                                )
                            ),

    source_type             VARCHAR(20) NOT NULL
                            CHECK (
                                source_type IN
                                (
                                    'PDF',
                                    'IMAGE'
                                )
                            ),

    issue_date              DATE,

    currency                VARCHAR(10),

    series                  VARCHAR(20),

    number                  VARCHAR(30),

    supplier_name           VARCHAR(250),

    supplier_ruc            CHAR(11),

    customer_name           VARCHAR(250),

    customer_ruc            CHAR(11),

    subtotal                NUMERIC(12,2),

    igv                     NUMERIC(12,2),

    total                   NUMERIC(12,2),

    description             TEXT,

    file_name               TEXT NOT NULL,

    file_path               TEXT NOT NULL,

    file_hash               VARCHAR(64) NOT NULL UNIQUE,

    ocr_engine              VARCHAR(100),

    confidence              NUMERIC(5,2),

    status                  VARCHAR(20) NOT NULL
                            CHECK (
                                status IN
                                (
                                    'PENDING',
                                    'PROCESSED',
                                    'ERROR'
                                )
                            ),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE documents IS
'Información extraída de cada comprobante.';



-- ============================================================================
-- TABLA: classification_corrections
-- ============================================================================
-- Permite conocer cuándo el contador corrige la clasificación propuesta
-- por Ollama.
-- ============================================================================

CREATE TABLE classification_corrections (

    id                      BIGSERIAL PRIMARY KEY,

    document_id             BIGINT NOT NULL
                            REFERENCES documents(id)
                            ON DELETE CASCADE,

    old_category_code       VARCHAR(20)
                            REFERENCES categories(code),

    new_category_code       VARCHAR(20)
                            REFERENCES categories(code),

    reason                  TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE classification_corrections IS
'Correcciones manuales realizadas por el contador.';



-- ============================================================================
-- ÍNDICES
-- ============================================================================

CREATE INDEX idx_documents_company
ON documents(company_id);

CREATE INDEX idx_documents_issue_date
ON documents(issue_date);

CREATE INDEX idx_documents_category
ON documents(category_code);

CREATE INDEX idx_documents_supplier_ruc
ON documents(supplier_ruc);

CREATE INDEX idx_documents_processing
ON documents(processing_run_id);

CREATE INDEX idx_processing_status
ON processing_runs(status);

CREATE INDEX idx_categories_active
ON categories(active);



-- ============================================================================
-- TRIGGER: updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS
$$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated_at
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_categories_updated_at
BEFORE UPDATE ON categories
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

COMMIT;
