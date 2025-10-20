-- Supabase schema for PrepChef pilot deployment
-- Includes base tables, indexes, and RLS configuration for multi-tenant county data ingestion.

-- Enable required extensions
create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;

-- Schema to isolate PrepChef ETL artifacts
create schema if not exists prepchef;

set search_path to prepchef, public;

-- Counties participating in the pilot
create table if not exists counties (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    state text not null,
    fips_code varchar(5) unique not null,
    timezone text not null,
    data_portal_url text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists counties_state_idx on counties (state);

-- External data sources (Socrata, ArcGIS, CSV uploads, etc.)
create table if not exists data_sources (
    id uuid primary key default uuid_generate_v4(),
    county_id uuid not null references counties(id) on delete cascade,
    provider text not null,
    dataset_identifier text not null,
    dataset_name text not null,
    fetch_frequency text not null default 'daily',
    auth_method text not null default 'public',
    metadata jsonb not null default '{}',
    is_enabled boolean not null default true,
    last_synced_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(county_id, provider, dataset_identifier)
);

create index if not exists data_sources_county_idx on data_sources (county_id);
create index if not exists data_sources_provider_idx on data_sources (provider);

-- Raw inspection payloads staged from ETL before normalization
create table if not exists staging_inspections (
    id bigserial primary key,
    data_source_id uuid not null references data_sources(id) on delete cascade,
    external_primary_key text not null,
    raw_payload jsonb not null,
    ingestion_run_id uuid not null,
    ingested_at timestamptz not null default now(),
    unique(data_source_id, external_primary_key, ingestion_run_id)
);

create index if not exists staging_inspections_source_idx on staging_inspections (data_source_id);
create index if not exists staging_inspections_run_idx on staging_inspections (ingestion_run_id);

-- Normalized inspections for downstream analytics
create table if not exists inspections (
    id uuid primary key default uuid_generate_v4(),
    county_id uuid not null references counties(id) on delete cascade,
    establishment_name text not null,
    establishment_address text,
    establishment_city text,
    establishment_zip text,
    inspection_date date not null,
    inspection_type text,
    inspection_score numeric,
    grade text,
    result text,
    violation_count integer,
    violations jsonb,
    source_record_id bigint not null references staging_inspections(id) on delete cascade,
    data_source_id uuid not null references data_sources(id) on delete cascade,
    ingestion_run_id uuid not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(county_id, data_source_id, source_record_id)
);

create index if not exists inspections_county_idx on inspections (county_id);
create index if not exists inspections_date_idx on inspections (inspection_date);
create index if not exists inspections_score_idx on inspections (inspection_score);

-- Audit trail of ETL executions
create table if not exists ingestion_runs (
    id uuid primary key default uuid_generate_v4(),
    county_id uuid not null references counties(id) on delete cascade,
    data_source_id uuid not null references data_sources(id) on delete cascade,
    status text not null check (status in ('pending', 'running', 'success', 'failed', 'partial')),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    record_count integer not null default 0,
    error_count integer not null default 0,
    error_message text,
    created_at timestamptz not null default now()
);

create index if not exists ingestion_runs_county_idx on ingestion_runs (county_id);
create index if not exists ingestion_runs_status_idx on ingestion_runs (status);

-- Service accounts/users allowed to read county-specific data
create table if not exists api_clients (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    contact_email text,
    api_key uuid not null default uuid_generate_v4(),
    allowed_county_ids uuid[] not null default '{}',
    created_at timestamptz not null default now(),
    last_used_at timestamptz
);

create unique index if not exists api_clients_api_key_idx on api_clients (api_key);

-- Helper function to check if requester can access a county
create or replace function prepchef.is_authorized_for_county(county uuid)
returns boolean
    language sql
    stable
    security definer
    set search_path = prepchef, public
as $$
    select case
        when auth.uid() is null then false
        when exists (
            select 1
            from prepchef.api_clients c
            where c.id = auth.uid()
              and (c.allowed_county_ids = '{}'::uuid[]
                   or county = any(c.allowed_county_ids))
        ) then true
        else false
    end;
$$;

-- Row Level Security configuration
alter table counties enable row level security;
alter table data_sources enable row level security;
alter table staging_inspections enable row level security;
alter table inspections enable row level security;
alter table ingestion_runs enable row level security;

-- Counties: restrict to allowed counties
create policy counties_select_policy on counties
for select using (
    prepchef.is_authorized_for_county(id)
);

create policy counties_insert_policy on counties
for insert with check (
    exists (
        select 1
        from prepchef.api_clients c
        where c.id = auth.uid()
    )
);

create policy counties_update_policy on counties
for update using (
    prepchef.is_authorized_for_county(id)
) with check (
    prepchef.is_authorized_for_county(id)
);

-- Data sources policy
create policy data_sources_select_policy on data_sources
for select using (
    prepchef.is_authorized_for_county(county_id)
);

create policy data_sources_modify_policy on data_sources
for all using (
    prepchef.is_authorized_for_county(county_id)
) with check (
    prepchef.is_authorized_for_county(county_id)
);

-- Staging inspections policy
create policy staging_inspections_select_policy on staging_inspections
for select using (
    prepchef.is_authorized_for_county((
        select county_id from prepchef.data_sources ds where ds.id = staging_inspections.data_source_id
    ))
);

create policy staging_inspections_modify_policy on staging_inspections
for all using (
    prepchef.is_authorized_for_county((
        select county_id from prepchef.data_sources ds where ds.id = staging_inspections.data_source_id
    ))
) with check (
    prepchef.is_authorized_for_county((
        select county_id from prepchef.data_sources ds where ds.id = staging_inspections.data_source_id
    ))
);

-- Inspections policy
create policy inspections_select_policy on inspections
for select using (
    prepchef.is_authorized_for_county(county_id)
);

create policy inspections_modify_policy on inspections
for all using (
    prepchef.is_authorized_for_county(county_id)
) with check (
    prepchef.is_authorized_for_county(county_id)
);

-- Ingestion runs policy
create policy ingestion_runs_select_policy on ingestion_runs
for select using (
    prepchef.is_authorized_for_county(county_id)
);

create policy ingestion_runs_modify_policy on ingestion_runs
for all using (
    prepchef.is_authorized_for_county(county_id)
) with check (
    prepchef.is_authorized_for_county(county_id)
);

-- API clients policy: only service role should modify; read allowed for authenticated users
alter table api_clients enable row level security;

create policy api_clients_select_policy on api_clients
for select using (
    auth.role() = 'service_role'
    or (auth.role() = 'authenticated' and auth.uid() = id)
);

create policy api_clients_modify_policy on api_clients
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- Grant select to anon/public for endpoints that expose aggregated data
grant usage on schema prepchef to anon, authenticated, service_role;
grant select on all tables in schema prepchef to service_role;

-- Seed five pilot counties (replace identifiers as needed)
insert into counties (name, state, fips_code, timezone, data_portal_url)
values
    ('Multnomah County', 'OR', '41051', 'America/Los_Angeles', 'https://data.multco.us'),
    ('King County', 'WA', '53033', 'America/Los_Angeles', 'https://data.kingcounty.gov'),
    ('Cook County', 'IL', '17031', 'America/Chicago', 'https://datacatalog.cookcountyil.gov'),
    ('Fulton County', 'GA', '13121', 'America/New_York', 'https://opendata.fultoncountyga.gov'),
    ('Travis County', 'TX', '48453', 'America/Chicago', 'https://data.austintexas.gov')
on conflict (fips_code) do update
set name = excluded.name,
    state = excluded.state,
    timezone = excluded.timezone,
    data_portal_url = excluded.data_portal_url,
    updated_at = now();

reset search_path;
