-- Migration 011: Facility Safety, ADA, and Grease Management
-- Part of Municipal Delta compliance sprint
-- Covers fire safety, ventilation, ADA accessibility, grease trap maintenance

-- Facility safety profile
CREATE TABLE IF NOT EXISTS facility_safety_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL UNIQUE,              -- One profile per kitchen
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,

  -- Fire safety
  fire_suppression_system TEXT,                 -- ansul, other, none
  fire_suppression_last_inspected TIMESTAMPTZ,
  fire_extinguisher_count INT DEFAULT 0,
  fire_extinguisher_last_serviced TIMESTAMPTZ,
  emergency_exit_count INT DEFAULT 0,

  -- Ventilation
  ventilation_type TEXT,                        -- type_1_hood, type_2_hood, mechanical
  ventilation_cert_doc_id UUID,
  ventilation_cert_expires_at DATE,

  -- Grease management
  grease_interceptor_installed BOOLEAN DEFAULT false,
  grease_interceptor_size_gallons INT,
  grease_service_cadence_days INT DEFAULT 90,   -- Typical: 30, 60, or 90
  last_grease_service_at TIMESTAMPTZ,
  grease_vendor TEXT,

  -- ADA
  ada_accessible BOOLEAN DEFAULT false,
  ada_features TEXT[],                          -- ['wheelchair_entrance','accessible_restroom','lowered_counters']
  ada_notes TEXT,

  -- General
  last_updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facility_safety_profiles_kitchen
  ON facility_safety_profiles(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_facility_safety_profiles_jurisdiction
  ON facility_safety_profiles(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_facility_safety_profiles_last_grease_service
  ON facility_safety_profiles(last_grease_service_at);

-- Grease service logs (compliance audit trail)
CREATE TABLE IF NOT EXISTS grease_service_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  serviced_at TIMESTAMPTZ NOT NULL,
  vendor TEXT NOT NULL,
  gallons_removed NUMERIC(8,2),
  manifest_number TEXT,
  manifest_doc_id UUID,                         -- Link to waste manifest document
  next_service_due DATE,
  technician_name TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_grease_service_logs_kitchen
  ON grease_service_logs(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_grease_service_logs_serviced_at
  ON grease_service_logs(serviced_at);
CREATE INDEX IF NOT EXISTS idx_grease_service_logs_next_due
  ON grease_service_logs(next_service_due);

-- Fire safety equipment logs
CREATE TABLE IF NOT EXISTS fire_equipment_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  equipment_type TEXT CHECK (equipment_type IN (
    'fire_extinguisher',
    'suppression_system',
    'smoke_detector',
    'heat_detector',
    'emergency_lighting'
  )) NOT NULL,
  equipment_identifier TEXT,                    -- Serial number, location tag
  service_type TEXT CHECK (service_type IN ('inspection','maintenance','repair','replacement')) NOT NULL,
  serviced_at TIMESTAMPTZ NOT NULL,
  serviced_by TEXT,                             -- Company or technician
  passed BOOLEAN,
  next_service_due DATE,
  cert_doc_id UUID,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fire_equipment_logs_kitchen
  ON fire_equipment_logs(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_fire_equipment_logs_next_due
  ON fire_equipment_logs(next_service_due);

-- Ventilation compliance
CREATE TABLE IF NOT EXISTS ventilation_inspections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  inspected_at TIMESTAMPTZ NOT NULL,
  inspector TEXT,
  certification_number TEXT,
  hood_type TEXT,                               -- type_1, type_2
  airflow_cfm INT,
  makeup_air_adequate BOOLEAN,
  duct_cleanliness TEXT CHECK (duct_cleanliness IN ('pass','fail','needs_cleaning')),
  passed BOOLEAN NOT NULL,
  expires_at DATE,
  cert_doc_id UUID,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ventilation_inspections_kitchen
  ON ventilation_inspections(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_ventilation_inspections_expires_at
  ON ventilation_inspections(expires_at);

-- ADA accommodation requests/tracking
CREATE TABLE IF NOT EXISTS ada_accommodations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  maker_id UUID,                                -- Who requested (if specific)
  accommodation_type TEXT NOT NULL,             -- 'mobility','visual','hearing','other'
  description TEXT NOT NULL,
  requested_at TIMESTAMPTZ DEFAULT NOW(),
  reviewed_at TIMESTAMPTZ,
  reviewed_by TEXT,
  status TEXT CHECK (status IN ('pending','approved','denied','completed')) DEFAULT 'pending',
  denial_reason TEXT,
  implemented_at TIMESTAMPTZ,
  cost_cents BIGINT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ada_accommodations_kitchen
  ON ada_accommodations(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_ada_accommodations_maker
  ON ada_accommodations(maker_id);
CREATE INDEX IF NOT EXISTS idx_ada_accommodations_status
  ON ada_accommodations(status);

-- Safety incident categories (extends incidents table if exists)
-- We'll create a separate table that links to incidents
CREATE TABLE IF NOT EXISTS safety_incident_details (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id UUID NOT NULL,                    -- REFERENCES incidents(id)
  category TEXT CHECK (category IN (
    'fire',
    'chemical_spill',
    'gas_leak',
    'electrical',
    'structural',
    'equipment_failure',
    'other'
  )) NOT NULL,
  equipment_involved TEXT,
  fire_dept_notified BOOLEAN DEFAULT false,
  fire_dept_response_time_minutes INT,
  evacuation_occurred BOOLEAN DEFAULT false,
  injuries_count INT DEFAULT 0,
  property_damage_cents BIGINT,
  root_cause TEXT,
  corrective_actions TEXT,
  follow_up_required BOOLEAN DEFAULT false,
  follow_up_completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_safety_incident_details_incident
  ON safety_incident_details(incident_id);
CREATE INDEX IF NOT EXISTS idx_safety_incident_details_category
  ON safety_incident_details(category);

-- Comments
COMMENT ON TABLE facility_safety_profiles IS 'Comprehensive safety profile for each kitchen';
COMMENT ON TABLE grease_service_logs IS 'Grease trap/interceptor service history';
COMMENT ON TABLE fire_equipment_logs IS 'Fire safety equipment maintenance logs';
COMMENT ON TABLE ventilation_inspections IS 'Hood and ventilation system certifications';
COMMENT ON TABLE ada_accommodations IS 'ADA accommodation requests and implementation';
COMMENT ON TABLE safety_incident_details IS 'Extended details for safety-related incidents';
