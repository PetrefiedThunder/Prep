-- Migration: Create reg_docs table for normalized regulatory documents
-- Version: 006
-- Date: 2025-03-30

BEGIN;

CREATE TABLE IF NOT EXISTS reg_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction TEXT NOT NULL,
    code_section TEXT NOT NULL,
    requirement_text TEXT NOT NULL,
    effective_date DATE,
    citation_url TEXT,
    sha256_hash TEXT UNIQUE NOT NULL,
    inserted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_reg_docs_sha256_hash ON reg_docs (sha256_hash);

COMMIT;
