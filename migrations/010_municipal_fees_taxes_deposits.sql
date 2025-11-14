-- Migration 010: Municipal Fees, Taxes, Deposits, and Penalties
-- Part of Municipal Delta compliance sprint
-- Covers city/county-specific transient occupancy tax, B&O tax, deposits, late penalties

-- Fee/tax schedules per jurisdiction
CREATE TABLE IF NOT EXISTS municipal_fee_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  code TEXT NOT NULL,                           -- TOT, B&O, KingCountyLodging, etc.
  display_name TEXT NOT NULL,
  description TEXT,
  kind TEXT CHECK (kind IN ('percent','flat_per_booking','flat_per_hour')) NOT NULL,
  value NUMERIC(10,6) NOT NULL,                 -- For percent: 0.1400 = 14%, for flat: cents
  applies_to TEXT[] NOT NULL,                   -- ['base','cleaning','platform_fee']
  effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
  expires_at DATE,
  remittance_info TEXT,                         -- How/where to remit
  citation TEXT,                                -- Legal reference
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_municipal_fee_schedules_jurisdiction
  ON municipal_fee_schedules(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_municipal_fee_schedules_effective
  ON municipal_fee_schedules(effective_date, expires_at);
CREATE INDEX IF NOT EXISTS idx_municipal_fee_schedules_code
  ON municipal_fee_schedules(code);

-- Security deposit policies per jurisdiction
CREATE TABLE IF NOT EXISTS municipal_deposit_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  min_deposit_cents BIGINT NOT NULL,            -- Minimum security deposit
  max_deposit_cents BIGINT,                     -- Maximum allowed
  calculation_rule TEXT,                        -- e.g., "percent_of_booking", "flat"
  hold_window_hours INT NOT NULL DEFAULT 72,    -- How long deposit can be held post-booking
  refund_window_hours INT,                      -- When must refund be issued
  interest_required BOOLEAN DEFAULT false,      -- Must pay interest on deposits?
  interest_rate_annual NUMERIC(6,4),
  effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
  expires_at DATE,
  citation TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_municipal_deposit_policies_jurisdiction
  ON municipal_deposit_policies(jurisdiction_id);

-- Late payment penalty policies
CREATE TABLE IF NOT EXISTS late_penalty_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  applies_to TEXT NOT NULL,                     -- 'booking','permit_renewal','tax_filing'
  threshold_hours INT NOT NULL,                 -- Penalty applies after this delay
  penalty_type TEXT CHECK (penalty_type IN ('percent','flat')) NOT NULL,
  penalty_value NUMERIC(10,4) NOT NULL,
  max_penalty_cents BIGINT,                     -- Cap on penalties
  compounds BOOLEAN DEFAULT false,
  compound_interval_hours INT,
  effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
  expires_at DATE,
  citation TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_late_penalty_policies_jurisdiction
  ON late_penalty_policies(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_late_penalty_policies_applies_to
  ON late_penalty_policies(applies_to);

-- Computed fees per booking (for audit trail)
CREATE TABLE IF NOT EXISTS booking_municipal_fees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL,                     -- REFERENCES bookings(id)
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  fee_schedule_id UUID REFERENCES municipal_fee_schedules(id),
  code TEXT NOT NULL,                           -- Same as fee_schedule code
  description TEXT,
  base_amount_cents BIGINT NOT NULL,            -- What the fee applied to
  computed_fee_cents BIGINT NOT NULL,
  computation_detail JSONB,                     -- {"value": 0.14, "kind": "percent"}
  computed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_booking_municipal_fees_booking
  ON booking_municipal_fees(booking_id);
CREATE INDEX IF NOT EXISTS idx_booking_municipal_fees_jurisdiction
  ON booking_municipal_fees(jurisdiction_id);

-- Security deposits held
CREATE TABLE IF NOT EXISTS booking_deposits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL,
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  deposit_cents BIGINT NOT NULL,
  held_at TIMESTAMPTZ DEFAULT NOW(),
  released_at TIMESTAMPTZ,
  release_reason TEXT,                          -- 'completed_ok','damage','late_cancellation'
  deducted_cents BIGINT DEFAULT 0,
  deduction_reason TEXT,
  refunded_cents BIGINT DEFAULT 0,
  refunded_at TIMESTAMPTZ,
  payment_intent_id TEXT,                       -- Stripe/payment gateway reference
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_booking_deposits_booking ON booking_deposits(booking_id);
CREATE INDEX IF NOT EXISTS idx_booking_deposits_released_at ON booking_deposits(released_at) WHERE released_at IS NULL;

-- Late penalties applied
CREATE TABLE IF NOT EXISTS applied_late_penalties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reference_id UUID NOT NULL,                   -- booking_id, permit_id, etc.
  reference_type TEXT NOT NULL,                 -- 'booking','permit','tax_filing'
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  policy_id UUID REFERENCES late_penalty_policies(id),
  late_by_hours INT NOT NULL,
  penalty_cents BIGINT NOT NULL,
  waived BOOLEAN DEFAULT false,
  waived_at TIMESTAMPTZ,
  waived_reason TEXT,
  paid_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applied_late_penalties_reference
  ON applied_late_penalties(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_applied_late_penalties_jurisdiction
  ON applied_late_penalties(jurisdiction_id);

-- Comments
COMMENT ON TABLE municipal_fee_schedules IS 'City/county taxes and fees (TOT, B&O, etc.)';
COMMENT ON TABLE municipal_deposit_policies IS 'Security deposit rules per jurisdiction';
COMMENT ON TABLE late_penalty_policies IS 'Late payment penalty schedules';
COMMENT ON TABLE booking_municipal_fees IS 'Computed fees per booking (audit trail)';
COMMENT ON TABLE booking_deposits IS 'Security deposits held and released';
COMMENT ON TABLE applied_late_penalties IS 'Late penalties applied to bookings/permits/filings';

-- Insert initial fee schedules
INSERT INTO municipal_fee_schedules (jurisdiction_id, code, display_name, kind, value, applies_to, citation) VALUES
  -- San Francisco Commercial Rents Tax
  (
    'san_francisco',
    'CRT',
    'Commercial Rents Tax',
    'percent',
    0.0350,
    ARRAY['base'],
    'SF Business and Tax Regulations Code Article 21'
  ),
  -- Portland Lodging Tax
  (
    'portland',
    'Lodging',
    'Multnomah County Lodging Tax',
    'percent',
    0.1150,
    ARRAY['base','cleaning','platform_fee'],
    'Multnomah County Code 12.600'
  ),
  -- Seattle/King County Lodging Tax
  (
    'seattle',
    'KingCountyLodging',
    'King County Lodging Tax',
    'percent',
    0.0200,
    ARRAY['base','cleaning'],
    'King County Code 6.27'
  ),
  -- Seattle B&O Tax
  (
    'seattle',
    'B&O',
    'Business & Occupation Tax',
    'percent',
    0.0044,
    ARRAY['platform_fee'],
    'Seattle Municipal Code 5.45'
  )
ON CONFLICT DO NOTHING;

-- Insert initial deposit policies
INSERT INTO municipal_deposit_policies (jurisdiction_id, min_deposit_cents, hold_window_hours, citation) VALUES
  ('san_francisco', 10000, 72, 'SF Health Code §6.15'),
  ('portland', 10000, 72, 'Industry standard'),
  ('seattle', 10000, 72, 'Industry standard')
ON CONFLICT DO NOTHING;
