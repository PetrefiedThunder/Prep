-- Migration 012: Calendars, Maintenance Windows, and Seasonal Restrictions
-- Part of Municipal Delta compliance sprint
-- Covers facility downtime, inspection conflicts, and seasonal booking restrictions

-- Maintenance windows (facility unavailable)
CREATE TABLE IF NOT EXISTS maintenance_windows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  reason TEXT NOT NULL,                         -- 'scheduled_maintenance','repair','inspection_prep','deep_clean'
  recurrence_rule TEXT,                         -- RRULE format if recurring
  created_by TEXT,
  approved_by TEXT,
  notify_affected_bookings BOOLEAN DEFAULT true,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT maintenance_window_valid_range CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_maintenance_windows_kitchen
  ON maintenance_windows(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_windows_timerange
  ON maintenance_windows USING GIST (
    kitchen_id,
    tstzrange(starts_at, ends_at, '[)')
  );

-- Seasonal restrictions per jurisdiction
CREATE TABLE IF NOT EXISTS seasonal_restrictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  product_type TEXT,                            -- 'outdoor_cooking', 'catering', 'food_truck', NULL for all
  restriction_type TEXT CHECK (restriction_type IN ('prohibited','conditional','advisory')) NOT NULL,
  starts_on DATE NOT NULL,                      -- When restriction begins each year
  ends_on DATE NOT NULL,                        -- When restriction ends each year
  recurs_annually BOOLEAN DEFAULT true,
  reason TEXT NOT NULL,                         -- 'fire_season', 'extreme_weather', 'festival_blackout'
  conditions TEXT,                              -- If 'conditional', what conditions allow?
  citation TEXT,
  effective_year INT,                           -- First year this applies
  expires_year INT,                             -- Last year (NULL = indefinite)
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT seasonal_restriction_valid_range CHECK (ends_on >= starts_on)
);

CREATE INDEX IF NOT EXISTS idx_seasonal_restrictions_jurisdiction
  ON seasonal_restrictions(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_seasonal_restrictions_product_type
  ON seasonal_restrictions(product_type);
CREATE INDEX IF NOT EXISTS idx_seasonal_restrictions_dates
  ON seasonal_restrictions(starts_on, ends_on);

-- Holiday/special event closures per jurisdiction
CREATE TABLE IF NOT EXISTS jurisdiction_closures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  closure_date DATE NOT NULL,
  closure_name TEXT NOT NULL,                   -- 'New Year', 'Thanksgiving', 'City Festival'
  affects_inspections BOOLEAN DEFAULT true,
  affects_permit_processing BOOLEAN DEFAULT true,
  recurs_annually BOOLEAN DEFAULT true,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jurisdiction_closures_jurisdiction
  ON jurisdiction_closures(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_closures_date
  ON jurisdiction_closures(closure_date);

-- Booking blackout dates (platform-wide or kitchen-specific)
CREATE TABLE IF NOT EXISTS booking_blackouts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id UUID,                              -- NULL = all kitchens in jurisdiction
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  reason TEXT NOT NULL,
  allow_override BOOLEAN DEFAULT false,         -- Can admin override?
  created_by TEXT NOT NULL,
  approved_by TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT blackout_valid_range CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_booking_blackouts_kitchen
  ON booking_blackouts(kitchen_id) WHERE kitchen_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_booking_blackouts_jurisdiction
  ON booking_blackouts(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_booking_blackouts_timerange
  ON booking_blackouts USING GIST (
    tstzrange(starts_at, ends_at, '[)')
  );

-- Inspection buffer rules (how much padding around inspections)
CREATE TABLE IF NOT EXISTS inspection_buffer_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  inspection_type_code TEXT NOT NULL,           -- Links to inspection_types
  buffer_before_hours INT DEFAULT 4,            -- Block bookings before inspection
  buffer_after_hours INT DEFAULT 2,             -- Block bookings after inspection
  reason TEXT,
  effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
  expires_at DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inspection_buffer_rules_jurisdiction
  ON inspection_buffer_rules(jurisdiction_id);

-- Maker availability preferences (opt-in feature)
CREATE TABLE IF NOT EXISTS maker_availability_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  maker_id UUID NOT NULL UNIQUE,
  preferred_days_of_week INT[],                 -- [1,2,3,4,5] for Mon-Fri
  preferred_time_ranges JSONB,                  -- [{"start":"09:00","end":"17:00"}]
  excluded_dates DATE[],                        -- Specific dates maker unavailable
  buffer_hours INT DEFAULT 0,                   -- Min hours between bookings
  max_hours_per_day INT,                        -- Maker's own limit
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_maker_availability_preferences_maker
  ON maker_availability_preferences(maker_id);

-- Calendar conflict log (when booking attempts fail due to conflicts)
CREATE TABLE IF NOT EXISTS calendar_conflict_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_attempt_id UUID,                      -- If from a booking attempt
  kitchen_id UUID NOT NULL,
  requested_start TIMESTAMPTZ NOT NULL,
  requested_end TIMESTAMPTZ NOT NULL,
  conflict_type TEXT CHECK (conflict_type IN (
    'existing_booking',
    'maintenance',
    'inspection',
    'blackout',
    'seasonal_restriction',
    'jurisdiction_closure',
    'buffer_violation',
    'maker_unavailable'
  )) NOT NULL,
  conflict_reference_id UUID,                   -- ID of conflicting record
  conflict_reference_type TEXT,                 -- Table name of conflict
  attempted_at TIMESTAMPTZ DEFAULT NOW(),
  attempted_by UUID,                            -- maker_id or admin_id
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_calendar_conflict_logs_kitchen
  ON calendar_conflict_logs(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_calendar_conflict_logs_attempted_at
  ON calendar_conflict_logs(attempted_at);
CREATE INDEX IF NOT EXISTS idx_calendar_conflict_logs_conflict_type
  ON calendar_conflict_logs(conflict_type);

-- Comments
COMMENT ON TABLE maintenance_windows IS 'Scheduled maintenance and unavailability windows';
COMMENT ON TABLE seasonal_restrictions IS 'Jurisdiction-specific seasonal booking restrictions';
COMMENT ON TABLE jurisdiction_closures IS 'Holiday/special event closures affecting inspections and permits';
COMMENT ON TABLE booking_blackouts IS 'Platform or kitchen-specific blackout dates';
COMMENT ON TABLE inspection_buffer_rules IS 'Time buffers around inspections to prevent booking conflicts';
COMMENT ON TABLE maker_availability_preferences IS 'Maker-specific availability and scheduling preferences';
COMMENT ON TABLE calendar_conflict_logs IS 'Log of booking attempts that failed due to calendar conflicts';

-- Insert common inspection buffer rules
INSERT INTO inspection_buffer_rules (jurisdiction_id, inspection_type_code, buffer_before_hours, buffer_after_hours, reason) VALUES
  ('san_francisco', 'health', 4, 2, 'Prep time before and cleanup time after health inspection'),
  ('san_francisco', 'fire', 2, 1, 'Setup and clearance for fire inspection'),
  ('portland', 'health', 4, 2, 'Standard health inspection buffer'),
  ('portland', 'fire', 2, 1, 'Standard fire inspection buffer'),
  ('seattle', 'health', 4, 2, 'Standard health inspection buffer'),
  ('seattle', 'fire', 2, 1, 'Standard fire inspection buffer')
ON CONFLICT DO NOTHING;
