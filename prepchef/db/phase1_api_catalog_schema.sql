-- PrepChef Phase 1 API Catalog Schema
-- This migration creates the Supabase/PostgreSQL schema for the dynamic API catalog
-- outlined in Phase 1 of the PrepChef data infrastructure roadmap.

create extension if not exists "pgcrypto";

create schema if not exists prepchef_phase1;
set search_path to prepchef_phase1, public;

grant usage on schema prepchef_phase1 to authenticated, anon, service_role;

alter default privileges in schema prepchef_phase1
  grant select, insert, update, delete on tables to authenticated, anon, service_role;

alter default privileges in schema prepchef_phase1
  grant usage, select on sequences to authenticated, anon, service_role;

-- Utility function to maintain updated_at timestamps.
create or replace function prepchef_phase1.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := timezone('utc', now());
  return new;
end;
$$;

-- Master table of counties and local jurisdictions tracked by PrepChef.
create table if not exists counties (
  id uuid primary key default gen_random_uuid(),
  fips_code char(5) not null unique,
  name text not null,
  state_abbr char(2) not null,
  timezone text,
  population integer,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create trigger set_counties_updated_at
before update on counties
for each row execute procedure prepchef_phase1.touch_updated_at();

-- Core catalog of data endpoints discovered per county.
create table if not exists data_sources (
  id uuid primary key default gen_random_uuid(),
  county_id uuid not null references counties(id) on delete cascade,
  endpoint_url text not null,
  platform text,
  schema_type text,
  schema_url text,
  authentication_type text,
  authentication_payload jsonb,
  refresh_cadence text,
  ingest_format text,
  first_seen_at timestamptz not null default timezone('utc', now()),
  last_discovered_at timestamptz,
  last_successful_fetch_at timestamptz,
  data_quality_score numeric(5,2),
  availability_status text not null default 'unknown',
  notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint data_sources_endpoint_unique unique (county_id, endpoint_url)
);

create trigger set_data_sources_updated_at
before update on data_sources
for each row execute procedure prepchef_phase1.touch_updated_at();

create index if not exists data_sources_platform_idx on data_sources (platform);
create index if not exists data_sources_availability_idx on data_sources (availability_status);
create index if not exists data_sources_last_discovered_idx on data_sources (last_discovered_at desc);

-- Table capturing automated discovery and sync executions.
create table if not exists discovery_runs (
  id bigint generated always as identity primary key,
  run_type text not null default 'discovery',
  triggered_by text,
  status text not null default 'running',
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz,
  summary jsonb not null default '{}'::jsonb
);

-- Detailed outcomes for each data source touched in a discovery run.
create table if not exists discovery_run_results (
  id bigint generated always as identity primary key,
  discovery_run_id bigint not null references discovery_runs(id) on delete cascade,
  data_source_id uuid references data_sources(id) on delete cascade,
  county_id uuid not null references counties(id) on delete cascade,
  outcome text not null,
  http_status integer,
  response_time_ms integer,
  delta jsonb,
  detected_at timestamptz not null default timezone('utc', now())
);

create index if not exists discovery_run_results_run_idx on discovery_run_results (discovery_run_id);
create index if not exists discovery_run_results_outcome_idx on discovery_run_results (outcome);

-- Lightweight tag system to group endpoints by characteristics (e.g., "Socrata", "Inspection Scores").
create table if not exists tags (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create trigger set_tags_updated_at
before update on tags
for each row execute procedure prepchef_phase1.touch_updated_at();

create table if not exists data_source_tags (
  data_source_id uuid not null references data_sources(id) on delete cascade,
  tag_id uuid not null references tags(id) on delete cascade,
  created_at timestamptz not null default timezone('utc', now()),
  primary key (data_source_id, tag_id)
);

-- View summarizing current catalog coverage.
create or replace view v_county_catalog_status as
select
  c.id as county_id,
  c.fips_code,
  c.name,
  c.state_abbr,
  count(ds.id) as endpoint_count,
  count(distinct case when ds.availability_status = 'healthy' then ds.id end) as healthy_endpoint_count,
  max(ds.last_discovered_at) as last_discovered_at,
  max(ds.last_successful_fetch_at) as last_successful_fetch_at
from counties c
left join data_sources ds on ds.county_id = c.id
group by c.id, c.fips_code, c.name, c.state_abbr;

-- Ensure Supabase roles have access to the newly created tables, views, and sequences.
grant select, insert, update, delete on all tables in schema prepchef_phase1 to authenticated, anon, service_role;
grant usage, select on all sequences in schema prepchef_phase1 to authenticated, anon, service_role;

-- Enable row level security so Supabase can enforce API policies.
alter table counties enable row level security;
alter table data_sources enable row level security;
alter table discovery_runs enable row level security;
alter table discovery_run_results enable row level security;
alter table tags enable row level security;
alter table data_source_tags enable row level security;

-- Example permissive policies intended for internal service roles. Adjust before production.
create policy if not exists counties_service_policy on counties
  for all
  using (true)
  with check (true);

create policy if not exists data_sources_service_policy on data_sources
  for all
  using (true)
  with check (true);

create policy if not exists discovery_runs_service_policy on discovery_runs
  for all
  using (true)
  with check (true);

create policy if not exists discovery_run_results_service_policy on discovery_run_results
  for all
  using (true)
  with check (true);

create policy if not exists tags_service_policy on tags
  for all
  using (true)
  with check (true);

create policy if not exists data_source_tags_service_policy on data_source_tags
  for all
  using (true)
  with check (true);

reset search_path;
