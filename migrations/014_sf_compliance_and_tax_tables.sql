-- San Francisco compliance and tax tables

create table if not exists sf_host_profiles (
  host_kitchen_id uuid primary key references host_kitchens(id),
  business_registration_certificate text not null,
  business_registration_expires date not null,
  health_permit_number text not null,
  health_permit_expires date not null,
  facility_type text check (facility_type in ('cooking_kitchen','commissary_non_cooking','mobile_food_commissary')) not null,
  zoning_use_district text not null,
  fire_suppression_certificate text,
  fire_last_inspection date,
  grease_trap_certificate text,
  grease_last_service date,
  tax_classification text check (tax_classification in ('lease_sublease','service_provider')) not null,
  lease_gross_receipts_ytd numeric(14,2) default 0,
  compliance_status text check (compliance_status in ('compliant','flagged','blocked')) not null default 'flagged',
  updated_at timestamptz not null default current_timestamp
);

create table if not exists sf_zoning_verifications (
  id uuid primary key,
  host_kitchen_id uuid references host_kitchens(id),
  address text not null,
  zoning_use_district text not null,
  kitchen_use_allowed boolean not null,
  verification_date timestamptz not null,
  manual_review_required boolean not null default false
);

create table if not exists sf_booking_compliance (
  booking_id uuid primary key references bookings(id),
  prebooking_status text check (prebooking_status in ('passed','flagged','blocked')) not null,
  issues text[] not null,
  evaluated_at timestamptz not null default current_timestamp
);

create table if not exists sf_tax_ledger (
  id uuid primary key,
  booking_id uuid references bookings(id),
  tax_jurisdiction text not null,
  tax_basis numeric(14,2) not null,
  tax_rate numeric(7,4) not null,
  tax_amount numeric(14,2) not null,
  created_at timestamptz not null default current_timestamp
);

create table if not exists sf_tax_reports (
  id uuid primary key,
  period_start date not null,
  period_end date not null,
  total_tax_collected numeric(14,2) not null,
  total_booking_amount numeric(14,2) not null,
  file_status text check (file_status in ('not_prepared','prepared','remitted')) not null default 'not_prepared',
  generated_at timestamptz
);

create table if not exists city_etl_runs (
  id uuid primary key,
  city text not null,
  run_date timestamptz not null,
  records_extracted int not null,
  records_changed int not null,
  status text check (status in ('success','partial','failure')) not null,
  diff_summary text
);
