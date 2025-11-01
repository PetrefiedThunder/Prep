-- Migration 008: Municipal Permits, Zoning, and Inspections
-- Part of Municipal Delta compliance sprint
-- Covers city-specific permit tracking, zoning verification, and inspection scheduling

-- Jurisdictions table (cities we operate in)
CREATE TABLE IF NOT EXISTS jurisdictions (
  id TEXT PRIMARY KEY,                          -- san_francisco | portland | seattle
  display_name TEXT NOT NULL,
  state_code VARCHAR(2) NOT NULL,
  health_code_citation TEXT,                    -- e.g., "§6.15 Shared Kitchen Facilities"
  portal_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Zoning districts for each jurisdiction
CREATE TABLE IF NOT EXISTS zoning_districts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  code TEXT NOT NULL,                           -- e.g., NC-3, EXd, SM-SLU
  name TEXT,
  description TEXT,
  requires_conditional_use BOOLEAN DEFAULT false,
  requires_neighborhood_notice BOOLEAN DEFAULT false,
  allows_shared_kitchen BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(jurisdiction_id, code)
);

CREATE INDEX IF NOT EXISTS idx_zoning_districts_jurisdiction ON zoning_districts(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_zoning_districts_code ON zoning_districts(code);

-- Facility zoning assignments
CREATE TABLE IF NOT EXISTS facility_zoning (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,                     -- REFERENCES kitchens(id) - assuming kitchens table exists
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  zoning_code TEXT NOT NULL,
  conditional_use_permit BOOLEAN DEFAULT false,
  neighborhood_notice_doc_id UUID,              -- Link to document storage
  verified_at TIMESTAMPTZ,
  verified_by TEXT,                             -- User/admin who verified
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facility_zoning_kitchen ON facility_zoning(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_facility_zoning_jurisdiction ON facility_zoning(jurisdiction_id);

-- Permit types and requirements
CREATE TABLE IF NOT EXISTS permit_types (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  code TEXT NOT NULL,                           -- shared_kitchen, TFE, commissary, fire, ventilation
  display_name TEXT NOT NULL,
  description TEXT,
  required BOOLEAN DEFAULT true,
  renewal_interval_months INT,                  -- NULL if doesn't expire
  issuing_agency TEXT,
  application_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(jurisdiction_id, code)
);

CREATE INDEX IF NOT EXISTS idx_permit_types_jurisdiction ON permit_types(jurisdiction_id);

-- Permits issued to facilities
CREATE TABLE IF NOT EXISTS permits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  permit_type_code TEXT NOT NULL,
  permit_number TEXT,
  issued_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  status TEXT CHECK (status IN ('active','pending','expired','revoked','suspended')) DEFAULT 'pending',
  document_id UUID,                             -- Link to stored permit document
  issuing_agency TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_permits_kitchen ON permits(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_permits_jurisdiction ON permits(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_permits_status ON permits(status);
CREATE INDEX IF NOT EXISTS idx_permits_expires_at ON permits(expires_at) WHERE expires_at IS NOT NULL;

-- Inspection types and schedules
CREATE TABLE IF NOT EXISTS inspection_types (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  code TEXT NOT NULL,                           -- health, fire, building, ventilation
  display_name TEXT NOT NULL,
  frequency_months INT,                         -- How often required
  buffer_hours INT DEFAULT 24,                  -- Block bookings ± buffer around inspection
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(jurisdiction_id, code)
);

-- Inspections scheduled or completed
CREATE TABLE IF NOT EXISTS inspections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  inspection_type_code TEXT NOT NULL,
  scheduled_for TIMESTAMPTZ NOT NULL,
  scheduled_end TIMESTAMPTZ,                    -- For blocking calendar
  status TEXT CHECK (status IN ('scheduled','completed','failed','canceled','rescheduled')) DEFAULT 'scheduled',
  result TEXT CHECK (result IN ('pass','conditional','fail')) NULL,
  score INT,                                    -- e.g., health inspection score
  report_doc_id UUID,
  inspector_name TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inspections_kitchen ON inspections(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_inspections_jurisdiction ON inspections(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_inspections_scheduled_for ON inspections(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_inspections_status ON inspections(status);

-- Track inspection violations
CREATE TABLE IF NOT EXISTS inspection_violations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  inspection_id UUID REFERENCES inspections(id) ON DELETE CASCADE,
  code TEXT NOT NULL,                           -- Violation code from health dept
  description TEXT NOT NULL,
  severity TEXT CHECK (severity IN ('critical','major','minor')) DEFAULT 'minor',
  corrected_at TIMESTAMPTZ,
  correction_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inspection_violations_inspection ON inspection_violations(inspection_id);
CREATE INDEX IF NOT EXISTS idx_inspection_violations_severity ON inspection_violations(severity) WHERE corrected_at IS NULL;

-- Comments for documentation
COMMENT ON TABLE jurisdictions IS 'Cities/municipalities where Prep operates';
COMMENT ON TABLE zoning_districts IS 'Zoning codes and their shared kitchen compatibility';
COMMENT ON TABLE facility_zoning IS 'Zoning assignments for each facility';
COMMENT ON TABLE permit_types IS 'Types of permits required per jurisdiction';
COMMENT ON TABLE permits IS 'Permits issued to facilities';
COMMENT ON TABLE inspection_types IS 'Types of inspections and their schedules';
COMMENT ON TABLE inspections IS 'Inspection events (past and scheduled)';
COMMENT ON TABLE inspection_violations IS 'Violations found during inspections';

-- Insert initial jurisdictions
INSERT INTO jurisdictions (id, display_name, state_code, health_code_citation) VALUES
  ('san_francisco', 'San Francisco', 'CA', '§6.15 Shared Kitchen Facilities'),
  ('portland', 'Portland', 'OR', 'Multnomah County Health Code Chapter 5'),
  ('seattle', 'Seattle', 'WA', 'Seattle Municipal Code 10.10')
ON CONFLICT (id) DO NOTHING;
