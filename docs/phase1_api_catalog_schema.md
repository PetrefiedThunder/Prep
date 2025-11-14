# PrepChef Phase 1 API Catalog Schema

This document describes the Supabase/PostgreSQL assets that back the Phase 1 dynamic API catalog. Use it alongside `prepchef/db/phase1_api_catalog_schema.sql` and `prepchef/db/phase1_ingestion_template.json` to seed and automate the discovery layer.

## Database Objects

### Schema: `prepchef_phase1`
All catalog tables live inside this schema to keep the Phase 1 assets isolated while the broader data platform evolves.

### Tables

| Table | Purpose |
| --- | --- |
| `counties` | Canonical roster of county or jurisdictional entities tracked by PrepChef. Stores FIPS metadata and local configuration details. |
| `data_sources` | Primary catalog of discovered food safety data endpoints, including authentication strategy, refresh cadence, and quality scoring metadata. |
| `discovery_runs` | Execution log for automated sweeps (GitHub Actions, n8n scenarios, manual scripts). |
| `discovery_run_results` | Row-level outcomes for each endpoint touched by a discovery run, allowing delta comparisons and error triage. |
| `tags` | Managed vocabulary for labeling endpoints (platform, data modality, compliance attributes). |
| `data_source_tags` | Join table linking catalog entries to tags. |

### View

- `v_county_catalog_status`: Summarizes coverage per county, including endpoint counts and last successful access timestamps.

### Extensions, Functions, and Policies

- Requires the `pgcrypto` extension for UUID generation.
- Provides a reusable `touch_updated_at` trigger function so mutation timestamps stay accurate.
- Enables Supabase row-level security (RLS) with permissive service policies. Lock these policies down before enabling direct client access.

## Bootstrap Workflow

1. **Run the migration** via Supabase SQL editor or `psql`:
   ```bash
   psql $SUPABASE_URL/postgres <<'SQL'
   \i prepchef/db/phase1_api_catalog_schema.sql
   SQL
   ```
2. **Seed initial data** by adapting the JSON template in `prepchef/db/phase1_ingestion_template.json`. Each ingestion payload should serialize into the `counties`, `data_sources`, and `discovery_runs` tables.
3. **Automate ingestion** through GitHub Actions or n8n scenarios that:
   - Upsert counties by `fips_code`.
   - Upsert data sources by `(county_id, endpoint_url)`.
   - Log discovery run metadata and per-endpoint outcomes.
4. **Monitor coverage** using the `v_county_catalog_status` view and expose it via PostgREST or Supabase’s auto-generated REST endpoints.

## JSON Ingestion Template

The template includes sections for `discovery_run`, `county`, and `data_source`. Replace placeholder values with live data before submitting the payload through your automation layer. Key fields:

- `platform`: Standardized to known providers (`socrata`, `opengov`, `arcgis`, `custom`, etc.).
- `schema_type`: High-level classification (`inspection_scores`, `violations`, `permits`).
- `authentication_payload`: Captures headers or credentials stored as Supabase secrets.
- `metadata.fields`: Maps external field names to PrepChef’s normalized schema for downstream ingestion.

## Next Enhancements

- Add materialized views for freshness scoring (e.g., median age of latest inspection per county).
- Introduce audit tables to capture manual overrides from the outreach/partnership workflow.
- Align `schema_type` and `metadata` keys with the forthcoming `prepchef_foodsafety_schema_v1.yaml` definition.
