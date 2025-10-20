-- PrepChef Phase 1 Supabase Schema for Dynamic API Catalog
-- This schema captures jurisdictions, API endpoints, and automated discovery/ingestion runs.

-- Enable extensions required for Supabase/ Postgres 14+
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- Enumerations for consistent domain values
CREATE TYPE platform_type AS ENUM (
    'socrata',
    'opengov',
    'arcgis',
    'usda',
    'state_portal',
    'custom_api',
    'manual_upload',
    'unknown'
);

CREATE TYPE endpoint_status AS ENUM (
    'active',
    'deprecated',
    'offline',
    'unstable',
    'unknown'
);

CREATE TYPE discovery_run_status AS ENUM (
    'scheduled',
    'in_progress',
    'succeeded',
    'partial',
    'failed'
);

CREATE TYPE auth_method AS ENUM (
    'none',
    'api_key',
    'oauth2',
    'http_basic',
    'cookie',
    'custom',
    'unknown'
);

-- Jurisdictions tracked in the PrepChef catalog
CREATE TABLE jurisdictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_code CHAR(2) NOT NULL,
    county_name TEXT NOT NULL,
    fips_state CHAR(2),
    fips_county CHAR(3),
    population_estimate INTEGER,
    timezone TEXT,
    data_sharing_priority INTEGER DEFAULT 3 CHECK (data_sharing_priority BETWEEN 1 AND 5),
    notes TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (state_code, county_name)
);

CREATE INDEX jurisdictions_fips_idx ON jurisdictions (fips_state, fips_county);

-- Platforms cataloged for re-use across endpoints (Socrata, OpenGov, etc.)
CREATE TABLE data_platforms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    platform_type platform_type NOT NULL,
    base_url TEXT,
    contact_email CITEXT,
    support_url TEXT,
    auth_method auth_method NOT NULL DEFAULT 'unknown',
    auth_notes TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (LOWER(name), platform_type)
);

CREATE INDEX data_platforms_type_idx ON data_platforms (platform_type);

-- Primary API catalog entries per jurisdiction
CREATE TABLE api_catalog_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction_id UUID NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
    platform_id UUID REFERENCES data_platforms(id) ON DELETE SET NULL,
    endpoint_url TEXT NOT NULL,
    dataset_name TEXT,
    dataset_uid TEXT,
    schema_type TEXT,
    content_format TEXT,
    availability_status endpoint_status NOT NULL DEFAULT 'unknown',
    auth_method auth_method NOT NULL DEFAULT 'unknown',
    auth_config JSONB DEFAULT '{}'::JSONB,
    refresh_interval_hours INTEGER,
    last_harvested_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    freshness_score NUMERIC(5,2) CHECK (freshness_score BETWEEN 0 AND 100),
    quality_score NUMERIC(5,2) CHECK (quality_score BETWEEN 0 AND 100),
    open_data_portal_url TEXT,
    schema_document_url TEXT,
    data_dictionary JSONB,
    sample_record JSONB,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (jurisdiction_id, endpoint_url)
);

CREATE INDEX api_catalog_entries_jurisdiction_idx ON api_catalog_entries (jurisdiction_id);
CREATE INDEX api_catalog_entries_status_idx ON api_catalog_entries (availability_status);
CREATE INDEX api_catalog_entries_tags_idx ON api_catalog_entries USING GIN (tags);
CREATE INDEX api_catalog_entries_metadata_idx ON api_catalog_entries USING GIN (metadata);

-- Discovery jobs orchestrated via n8n/Make/GitHub Actions sweeps
CREATE TABLE discovery_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_type platform_type,
    run_status discovery_run_status NOT NULL DEFAULT 'scheduled',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    triggered_by TEXT NOT NULL, -- e.g., 'github_actions', 'manual', 'n8n'
    query JSONB NOT NULL, -- search parameters used for discovery
    result_summary JSONB,
    error_log TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX discovery_jobs_platform_idx ON discovery_jobs (platform_type);
CREATE INDEX discovery_jobs_status_idx ON discovery_jobs (run_status);

-- Linking discovery runs to catalog entries they touched
CREATE TABLE discovery_job_catalog_entries (
    discovery_job_id UUID NOT NULL REFERENCES discovery_jobs(id) ON DELETE CASCADE,
    catalog_entry_id UUID NOT NULL REFERENCES api_catalog_entries(id) ON DELETE CASCADE,
    change_type TEXT NOT NULL CHECK (change_type IN ('created', 'updated', 'unchanged')),
    diff JSONB,
    PRIMARY KEY (discovery_job_id, catalog_entry_id)
);

-- Ingestion run tracking for Supabase pipelines or Airbyte connectors
CREATE TABLE ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_entry_id UUID NOT NULL REFERENCES api_catalog_entries(id) ON DELETE CASCADE,
    job_id UUID REFERENCES discovery_jobs(id) ON DELETE SET NULL,
    run_status discovery_run_status NOT NULL DEFAULT 'scheduled',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    rows_ingested INTEGER,
    checksum TEXT,
    error_summary JSONB,
    storage_location TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ingestion_runs_catalog_idx ON ingestion_runs (catalog_entry_id);
CREATE INDEX ingestion_runs_status_idx ON ingestion_runs (run_status);

-- Materialized view scaffold for reporting freshness across counties
CREATE MATERIALIZED VIEW api_catalog_freshness AS
SELECT
    j.state_code,
    j.county_name,
    COUNT(c.id) AS endpoint_count,
    AVG(c.freshness_score) AS avg_freshness_score,
    AVG(c.quality_score) AS avg_quality_score,
    MAX(c.last_seen_at) AS last_seen_at,
    MAX(c.last_harvested_at) AS last_harvested_at
FROM jurisdictions j
LEFT JOIN api_catalog_entries c ON c.jurisdiction_id = j.id
GROUP BY j.state_code, j.county_name;

CREATE INDEX api_catalog_freshness_state_idx ON api_catalog_freshness (state_code, county_name);

-- Refresh helper
CREATE OR REPLACE FUNCTION refresh_api_catalog_freshness()
RETURNS VOID LANGUAGE SQL AS $$
    REFRESH MATERIALIZED VIEW CONCURRENTLY api_catalog_freshness;
$$;
