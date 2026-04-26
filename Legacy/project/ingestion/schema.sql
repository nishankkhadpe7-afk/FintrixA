-- ============================================================
-- RBI Circular Ingestion — Database Schema
-- ============================================================

-- Raw documents: stores EXACT content from RBI circulars (immutable)
CREATE TABLE IF NOT EXISTS raw_documents (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(50) NOT NULL DEFAULT 'RBI',
    title           TEXT NOT NULL,
    url             TEXT UNIQUE NOT NULL,
    published_date  TIMESTAMP,
    content         TEXT NOT NULL,
    content_hash    VARCHAR(64) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Index for deduplication lookups
CREATE INDEX IF NOT EXISTS idx_raw_documents_url ON raw_documents (url);
CREATE INDEX IF NOT EXISTS idx_raw_documents_content_hash ON raw_documents (content_hash);

-- Processed documents: tracks which URLs have been sent through LLM pipeline
CREATE TABLE IF NOT EXISTS processed_documents (
    id              SERIAL PRIMARY KEY,
    raw_document_id INTEGER REFERENCES raw_documents(id),
    url             TEXT UNIQUE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, success, failed
    result          JSONB,
    error           TEXT,
    processed_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_documents_url ON processed_documents (url);
CREATE INDEX IF NOT EXISTS idx_processed_documents_status ON processed_documents (status);

-- Rules: stores normalized, canonicalized rules with versioning
CREATE TABLE IF NOT EXISTS rules (
    id              SERIAL PRIMARY KEY,
    rule_hash       VARCHAR(64) UNIQUE NOT NULL,
    rule_id         VARCHAR(32) NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    type            VARCHAR(50) NOT NULL,
    title           TEXT DEFAULT '',
    regulator       VARCHAR(50) DEFAULT 'UNKNOWN',
    action          TEXT NOT NULL,
    description     TEXT DEFAULT '',
    canonical_rule  JSONB NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(rule_id, version)
);

CREATE INDEX IF NOT EXISTS idx_rules_rule_id ON rules (rule_id);
CREATE INDEX IF NOT EXISTS idx_rules_rule_hash ON rules (rule_hash);
CREATE INDEX IF NOT EXISTS idx_rules_type ON rules (type);

-- Conditions: denormalized condition storage for querying
CREATE TABLE IF NOT EXISTS conditions (
    id              SERIAL PRIMARY KEY,
    rule_id         INTEGER REFERENCES rules(id) ON DELETE CASCADE,
    field           VARCHAR(100) NOT NULL,
    operator        VARCHAR(10) NOT NULL,
    value           JSONB NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conditions_rule_id ON conditions (rule_id);
CREATE INDEX IF NOT EXISTS idx_conditions_field ON conditions (field);

-- Rule changes: tracks diffs between rule versions
CREATE TABLE IF NOT EXISTS rule_changes (
    id              SERIAL PRIMARY KEY,
    rule_id         VARCHAR(32) NOT NULL,
    version_from    INTEGER NOT NULL,
    version_to      INTEGER NOT NULL,
    diff            JSONB NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rule_changes_rule_id ON rule_changes (rule_id);
