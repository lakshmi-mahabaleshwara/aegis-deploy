-- =============================================================================
-- Aegis Deploy — Identity Vault: Initial Schema
-- =============================================================================
-- Target: PostgreSQL 15+
-- This migration creates the core tables for the Identity Vault.
-- Run from a secure, restricted network — this database must never be
-- exposed to analytics users or researchers.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Identity Mappings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_mappings (
    id              SERIAL PRIMARY KEY,
    original_id     VARCHAR(512) NOT NULL UNIQUE,
    deid_token      VARCHAR(128) NOT NULL,
    modality        VARCHAR(16),
    source_type     VARCHAR(32)  NOT NULL DEFAULT 's3',
    batch_id        VARCHAR(64)  NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for lookup performance
CREATE INDEX IF NOT EXISTS ix_identity_original_id ON identity_mappings (original_id);
CREATE INDEX IF NOT EXISTS ix_identity_deid_token  ON identity_mappings (deid_token);
CREATE INDEX IF NOT EXISTS ix_identity_batch       ON identity_mappings (batch_id);

-- ---------------------------------------------------------------------------
-- Audit Log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id              SERIAL PRIMARY KEY,
    action          VARCHAR(64)  NOT NULL,
    actor           VARCHAR(128) NOT NULL DEFAULT 'aegis-deploy',
    original_id     VARCHAR(512),
    details         TEXT,
    timestamp       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMIT;
