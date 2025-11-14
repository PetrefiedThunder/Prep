-- Migration 013: Emergency Contacts, Waste Management, and Neighborhood Complaints
-- Part of Municipal Delta compliance sprint
-- Covers health department contacts, outbreak protocols, waste compliance, and complaint tracking

-- Health department emergency contacts per jurisdiction
CREATE TABLE IF NOT EXISTS health_department_contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  dept_name TEXT NOT NULL,
  hotline TEXT,
  after_hours TEXT,
  email TEXT,
  website TEXT,
  outbreak_reporting_url TEXT,
  illness_threshold_notification INT DEFAULT 3,  -- Auto-notify if >= this many illnesses
  priority_response_sla_hours INT,              -- Expected response time for priority issues
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(jurisdiction_id)
);

CREATE INDEX IF NOT EXISTS idx_health_department_contacts_jurisdiction
  ON health_department_contacts(jurisdiction_id);

-- Extend incidents table with health/outbreak fields
-- (Assumes incidents table exists from previous migrations)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'incidents'
    AND column_name = 'category'
  ) THEN
    ALTER TABLE incidents
      ADD COLUMN category TEXT CHECK (category IN ('illness','injury','facility','equipment','other'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'incidents'
    AND column_name = 'notified_health_dept_at'
  ) THEN
    ALTER TABLE incidents
      ADD COLUMN notified_health_dept_at TIMESTAMPTZ;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'incidents'
    AND column_name = 'outbreak_suspected'
  ) THEN
    ALTER TABLE incidents
      ADD COLUMN outbreak_suspected BOOLEAN DEFAULT false;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'incidents'
    AND column_name = 'jurisdiction_id'
  ) THEN
    ALTER TABLE incidents
      ADD COLUMN jurisdiction_id TEXT REFERENCES jurisdictions(id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'incidents'
    AND column_name = 'affected_count'
  ) THEN
    ALTER TABLE incidents
      ADD COLUMN affected_count INT DEFAULT 1;
  END IF;
END $$;

-- Illness tracking for outbreak detection
CREATE TABLE IF NOT EXISTS illness_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id UUID,                             -- REFERENCES incidents(id) if linked
  kitchen_id UUID NOT NULL,
  booking_id UUID,                              -- If linked to specific booking
  reported_at TIMESTAMPTZ DEFAULT NOW(),
  reported_by TEXT,                             -- 'maker','customer','health_dept','anonymous'
  illness_type TEXT,                            -- 'foodborne','allergic_reaction','other'
  symptoms TEXT[],                              -- ['nausea','vomiting','diarrhea','fever']
  onset_date DATE,
  affected_count INT DEFAULT 1,
  hospitalized_count INT DEFAULT 0,
  food_items_suspected TEXT[],
  lab_confirmed BOOLEAN DEFAULT false,
  pathogen TEXT,                                -- If lab confirmed: salmonella, e.coli, etc.
  health_dept_case_number TEXT,
  status TEXT CHECK (status IN ('reported','investigating','closed')) DEFAULT 'reported',
  investigation_notes TEXT,
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_illness_reports_kitchen ON illness_reports(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_illness_reports_booking ON illness_reports(booking_id);
CREATE INDEX IF NOT EXISTS idx_illness_reports_onset_date ON illness_reports(onset_date);
CREATE INDEX IF NOT EXISTS idx_illness_reports_status ON illness_reports(status);

-- Neighborhood complaints
CREATE TABLE IF NOT EXISTS neighborhood_complaints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  received_at TIMESTAMPTZ DEFAULT NOW(),
  channel TEXT CHECK (channel IN ('phone','email','311','web_form','in_person')) NOT NULL,
  category TEXT CHECK (category IN ('noise','odor','traffic','parking','hours','trash','other')) NOT NULL,
  description TEXT NOT NULL,
  complainant_name TEXT,                        -- May be anonymous
  complainant_contact TEXT,
  severity TEXT CHECK (severity IN ('low','medium','high','urgent')) DEFAULT 'medium',
  validated BOOLEAN,                            -- Did we confirm the complaint?
  investigated_at TIMESTAMPTZ,
  investigated_by TEXT,
  findings TEXT,
  resolved_at TIMESTAMPTZ,
  resolution TEXT,
  follow_up_required BOOLEAN DEFAULT false,
  follow_up_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_neighborhood_complaints_kitchen
  ON neighborhood_complaints(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_neighborhood_complaints_jurisdiction
  ON neighborhood_complaints(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_neighborhood_complaints_received_at
  ON neighborhood_complaints(received_at);
CREATE INDEX IF NOT EXISTS idx_neighborhood_complaints_category
  ON neighborhood_complaints(category);
CREATE INDEX IF NOT EXISTS idx_neighborhood_complaints_resolved_at
  ON neighborhood_complaints(resolved_at) WHERE resolved_at IS NULL;

-- Quiet hours violations (subset of noise complaints)
CREATE TABLE IF NOT EXISTS quiet_hours_violations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  complaint_id UUID REFERENCES neighborhood_complaints(id) ON DELETE CASCADE,
  kitchen_id UUID NOT NULL,
  booking_id UUID,                              -- If linked to specific booking
  occurred_at TIMESTAMPTZ NOT NULL,
  jurisdiction_quiet_start TIME,                -- e.g., '22:00'
  jurisdiction_quiet_end TIME,                  -- e.g., '06:00'
  violation_confirmed BOOLEAN,
  warning_issued BOOLEAN DEFAULT false,
  warning_issued_at TIMESTAMPTZ,
  fine_assessed BOOLEAN DEFAULT false,
  fine_cents BIGINT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quiet_hours_violations_kitchen
  ON quiet_hours_violations(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_quiet_hours_violations_booking
  ON quiet_hours_violations(booking_id);
CREATE INDEX IF NOT EXISTS idx_quiet_hours_violations_occurred_at
  ON quiet_hours_violations(occurred_at);

-- Waste management policies per jurisdiction
CREATE TABLE IF NOT EXISTS waste_management_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  requires_food_waste_recycling BOOLEAN DEFAULT false,
  requires_composting BOOLEAN DEFAULT false,
  requires_grease_recycling BOOLEAN DEFAULT true,
  requires_hazmat_plan BOOLEAN DEFAULT false,
  licensed_hauler_required BOOLEAN DEFAULT false,
  reporting_frequency TEXT,                     -- 'monthly','quarterly','annually'
  citation TEXT,
  effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
  expires_at DATE,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_waste_management_policies_jurisdiction
  ON waste_management_policies(jurisdiction_id);

-- Waste disposal events
CREATE TABLE IF NOT EXISTS waste_disposal_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  booking_id UUID,                              -- If linked to specific booking
  disposed_at TIMESTAMPTZ NOT NULL,
  waste_type TEXT CHECK (waste_type IN (
    'food_waste_compost',
    'food_waste_landfill',
    'grease',
    'cooking_oil',
    'hazardous',
    'recyclables',
    'general_trash'
  )) NOT NULL,
  quantity_pounds NUMERIC(10,2),
  hauler_name TEXT,
  manifest_number TEXT,
  manifest_doc_id UUID,
  disposal_site TEXT,
  disposal_method TEXT,                         -- 'composted','incinerated','landfill','recycled'
  compliance_verified BOOLEAN DEFAULT false,
  verified_by TEXT,
  verified_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_waste_disposal_events_kitchen
  ON waste_disposal_events(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_waste_disposal_events_booking
  ON waste_disposal_events(booking_id);
CREATE INDEX IF NOT EXISTS idx_waste_disposal_events_disposed_at
  ON waste_disposal_events(disposed_at);
CREATE INDEX IF NOT EXISTS idx_waste_disposal_events_waste_type
  ON waste_disposal_events(waste_type);

-- Complaint escalation thresholds
CREATE TABLE IF NOT EXISTS complaint_escalation_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  complaint_category TEXT NOT NULL,             -- noise, odor, etc.
  threshold_count INT NOT NULL,                 -- Number of complaints
  window_days INT NOT NULL,                     -- Within this many days
  action TEXT NOT NULL,                         -- 'warning','soft_block','suspend_listings','revoke_permit'
  action_severity TEXT CHECK (action_severity IN ('low','medium','high','critical')) DEFAULT 'medium',
  notify_host BOOLEAN DEFAULT true,
  notify_jurisdiction BOOLEAN DEFAULT false,
  auto_apply BOOLEAN DEFAULT false,             -- Automatically apply action?
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_complaint_escalation_rules_jurisdiction
  ON complaint_escalation_rules(jurisdiction_id);

-- Comments
COMMENT ON TABLE health_department_contacts IS 'Emergency contact info for local health departments';
COMMENT ON TABLE illness_reports IS 'Foodborne illness and outbreak tracking';
COMMENT ON TABLE neighborhood_complaints IS 'Complaints from neighbors and community';
COMMENT ON TABLE quiet_hours_violations IS 'Noise complaints during designated quiet hours';
COMMENT ON TABLE waste_management_policies IS 'Jurisdiction waste/recycling requirements';
COMMENT ON TABLE waste_disposal_events IS 'Waste disposal and hauling logs';
COMMENT ON TABLE complaint_escalation_rules IS 'Automated complaint escalation thresholds';

-- Insert initial health department contacts
INSERT INTO health_department_contacts (
  jurisdiction_id,
  dept_name,
  hotline,
  email,
  outbreak_reporting_url
) VALUES
  (
    'san_francisco',
    'San Francisco Department of Public Health',
    '415-554-2500',
    'ehs.complaints@sfdph.org',
    'https://www.sfdph.org/dph/EH/Food/Complaints.asp'
  ),
  (
    'portland',
    'Multnomah County Health Department',
    '503-988-3674',
    'foodborne.illness@multco.us',
    'https://multco.us/health/food-safety/report-foodborne-illness'
  ),
  (
    'seattle',
    'Public Health - Seattle & King County',
    '206-263-9566',
    'food.safety@kingcounty.gov',
    'https://kingcounty.gov/depts/health/environmental-health/food-safety/report-illness.aspx'
  )
ON CONFLICT (jurisdiction_id) DO NOTHING;

-- Insert waste management policies
INSERT INTO waste_management_policies (
  jurisdiction_id,
  requires_food_waste_recycling,
  requires_composting,
  citation
) VALUES
  ('san_francisco', true, true, 'SF Environment Code Chapter 19'),
  ('portland', true, false, 'Portland City Code 17.102'),
  ('seattle', true, false, 'Seattle Municipal Code 21.36')
ON CONFLICT DO NOTHING;

-- Insert complaint escalation rules
INSERT INTO complaint_escalation_rules (
  jurisdiction_id,
  complaint_category,
  threshold_count,
  window_days,
  action,
  action_severity
) VALUES
  ('san_francisco', 'noise', 3, 30, 'warning', 'medium'),
  ('san_francisco', 'noise', 5, 60, 'soft_block', 'high'),
  ('portland', 'noise', 3, 30, 'warning', 'medium'),
  ('seattle', 'noise', 3, 30, 'warning', 'medium')
ON CONFLICT DO NOTHING;
