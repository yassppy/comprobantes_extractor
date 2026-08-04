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
-- Empresas del contador a las que pertenecen los comprobantes.
-- Los campos SUNAT se rellenan al validar el RUC via Playwright.
-- ============================================================================

CREATE TABLE companies (

    id                  BIGSERIAL PRIMARY KEY,

    -- Datos de registro
    ruc                 CHAR(11)        NOT NULL UNIQUE,
    business_name       VARCHAR(255)    NOT NULL,
    trade_name          VARCHAR(255),
    fiscal_address      TEXT,

    -- Estado SUNAT (sincronizado via scraping)
    sunat_status        VARCHAR(50),            -- ACTIVO | BAJA DEFINITIVA | ...
    sunat_condition     VARCHAR(50),            -- HABIDO | NO HABIDO | NO HALLADO
    sunat_is_valid      BOOLEAN         NOT NULL DEFAULT FALSE,
    sunat_validated_at  TIMESTAMPTZ,

    -- Estado interno
    active              BOOLEAN         NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE  companies                  IS 'Empresas del contador. RUC validado contra SUNAT.';
COMMENT ON COLUMN companies.sunat_is_valid   IS 'TRUE si estado=ACTIVO y condicion=HABIDO.';
COMMENT ON COLUMN companies.sunat_validated_at IS 'Última vez que se consultó SUNAT para esta empresa.';



-- ============================================================================
-- TABLA: business_partners
-- ============================================================================
-- Proveedores y clientes únicos identificados por su documento.
-- Evita repetir razón social en cada comprobante.
-- Los RUC de 11 dígitos se pueden validar contra SUNAT.
-- Los DNI de 8 dígitos se pueden validar con sunat pero el opcional con 0 no.
-- ============================================================================

CREATE TABLE business_partners (

    id                  BIGSERIAL PRIMARY KEY,

    document_type       VARCHAR(20)     NOT NULL
                        CHECK (document_type IN ('RUC', 'DNI', 'VENTA MENOR')),

    document_number     VARCHAR(11)     NOT NULL UNIQUE,

    business_name       VARCHAR(255)    NOT NULL,

    -- Campos SUNAT (solo aplica cuando document_type = 'RUC')
    trade_name          VARCHAR(255),
    fiscal_address      TEXT,
    sunat_status        VARCHAR(50),            -- ACTIVO | BAJA DEFINITIVA | ...
    sunat_condition     VARCHAR(50),            -- HABIDO | NO HABIDO | NO HALLADO
    sunat_is_valid      BOOLEAN         NOT NULL DEFAULT FALSE,
    sunat_validated_at  TIMESTAMPTZ,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE  business_partners                    IS 'Proveedores y clientes normalizados por documento.';
COMMENT ON COLUMN business_partners.sunat_is_valid     IS 'TRUE si estado=ACTIVO y condicion=HABIDO. Solo aplica para RUC.';
COMMENT ON COLUMN business_partners.sunat_validated_at IS 'Última vez que se consultó SUNAT para este socio.';



-- ============================================================================
-- TABLA: categories
-- ============================================================================
-- Catálogo sincronizado desde categories.yaml
-- Ollama únicamente devuelve el código de categoría.
-- ============================================================================

CREATE TABLE categories (

    code            VARCHAR(20)     PRIMARY KEY,
    name            VARCHAR(150)    NOT NULL,
    description     TEXT,
    active          BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE categories IS 'Catálogo de categorías sincronizado desde YAML.';



-- ============================================================================
-- TABLA: processing_runs
-- ============================================================================
-- Cada ejecución representa un lote de procesamiento.
-- ============================================================================

CREATE TABLE processing_runs (

    id                  BIGSERIAL PRIMARY KEY,

    company_id          BIGINT          NOT NULL
                        REFERENCES companies(id),

    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,

    total_files         INTEGER         NOT NULL DEFAULT 0,
    processed_files     INTEGER         NOT NULL DEFAULT 0,
    failed_files        INTEGER         NOT NULL DEFAULT 0,
    duration_seconds    INTEGER,

    status              VARCHAR(20)     NOT NULL
                        CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE processing_runs IS 'Historial de ejecuciones del extractor por empresa.';



-- ============================================================================
-- TABLA: documents
-- ============================================================================
-- Información principal extraída de cada comprobante.
-- El socio de negocio (proveedor o cliente) se referencia via
-- business_partner_id para evitar duplicar razón social y RUC.
-- ============================================================================

CREATE TABLE documents (

    id                      BIGSERIAL PRIMARY KEY,

    processing_run_id       BIGINT          NOT NULL
                            REFERENCES processing_runs(id),

    company_id              BIGINT          NOT NULL
                            REFERENCES companies(id),

    -- Socio de negocio normalizado (proveedor en compras, cliente en ventas)
    business_partner_id     BIGINT
                            REFERENCES business_partners(id)
                            ON DELETE SET NULL,

    category_code           VARCHAR(20)
                            REFERENCES categories(code),

    -- Tipo de operación y origen del archivo
    document_type           VARCHAR(20)     NOT NULL
                            CHECK (document_type IN ('SALE', 'PURCHASE')),

    source_type             VARCHAR(20)     NOT NULL
                            CHECK (source_type IN ('PDF', 'IMAGE')),

    -- Datos del comprobante
    invoice_type            VARCHAR(60),            -- FACTURA ELECTRONICA, BOLETA DE VENTA, etc.
    issue_date              DATE,
    currency                VARCHAR(20),
    series                  VARCHAR(20),
    number                  VARCHAR(30),

    -- Montos
    subtotal                NUMERIC(12,2),
    igv                     NUMERIC(12,2),
    total                   NUMERIC(12,2),

    -- Descripción del bien/servicio
    description             TEXT,

    -- Metadata del archivo
    file_name               TEXT            NOT NULL,
    file_path               TEXT            NOT NULL,
    file_hash               VARCHAR(64)     NOT NULL UNIQUE,    -- SHA-256, evita duplicados (REQ-7 R2)
    ocr_engine              VARCHAR(100),
    confidence              NUMERIC(5,2),

    status                  VARCHAR(20)     NOT NULL
                            CHECK (status IN ('PENDING', 'PROCESSED', 'ERROR')),

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE  documents               IS 'Información extraída de cada comprobante.';
COMMENT ON COLUMN documents.file_hash     IS 'SHA-256 del archivo. Evita almacenar duplicados (REQ-7 R2).';
COMMENT ON COLUMN documents.invoice_type  IS 'Tipo normalizado: FACTURA ELECTRONICA, BOLETA DE VENTA, etc.';



-- ============================================================================
-- TABLA: classification_corrections
-- ============================================================================
-- Correcciones manuales del contador sobre la categoría asignada por Ollama.
-- ============================================================================

CREATE TABLE classification_corrections (

    id                  BIGSERIAL PRIMARY KEY,

    document_id         BIGINT          NOT NULL
                        REFERENCES documents(id)
                        ON DELETE CASCADE,

    old_category_code   VARCHAR(20)
                        REFERENCES categories(code),

    new_category_code   VARCHAR(20)
                        REFERENCES categories(code),

    reason              TEXT,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE classification_corrections IS 'Correcciones manuales de categoría realizadas por el contador.';



-- ============================================================================
-- ÍNDICES
-- ============================================================================

-- documents
CREATE INDEX idx_documents_company          ON documents(company_id);
CREATE INDEX idx_documents_partner          ON documents(business_partner_id);
CREATE INDEX idx_documents_issue_date       ON documents(issue_date);
CREATE INDEX idx_documents_category         ON documents(category_code);
CREATE INDEX idx_documents_processing       ON documents(processing_run_id);
CREATE INDEX idx_documents_type             ON documents(document_type);

-- business_partners
CREATE INDEX idx_partners_doc_number        ON business_partners(document_number);
CREATE INDEX idx_partners_sunat_valid       ON business_partners(sunat_is_valid);

-- processing_runs
CREATE INDEX idx_runs_company               ON processing_runs(company_id);
CREATE INDEX idx_runs_status                ON processing_runs(status);

-- categories
CREATE INDEX idx_categories_active          ON categories(active);

-- companies
CREATE INDEX idx_companies_sunat_valid      ON companies(sunat_is_valid);



-- ============================================================================
-- FUNCIÓN + TRIGGERS: updated_at automático
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_business_partners_updated_at
    BEFORE UPDATE ON business_partners
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;
