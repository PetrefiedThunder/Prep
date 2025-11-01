-- Migration 009: Municipal Insurance Requirements and COI Validation
-- Part of Municipal Delta compliance sprint
-- Covers city-specific insurance minimums, COI tracking, and additional insured validation

-- Insurance requirements per jurisdiction
CREATE TABLE IF NOT EXISTS municipal_insurance_requirements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  liability_min_cents BIGINT NOT NULL,          -- General liability minimum
  products_completed_ops_min_cents BIGINT,      -- Products & completed operations
  aggregate_min_cents BIGINT NOT NULL,          -- Aggregate coverage
  requires_additional_insured BOOLEAN DEFAULT true,
  additional_insured_legal_name TEXT,           -- Exact string that must appear on COI
  requires_workers_comp BOOLEAN DEFAULT true,
  workers_comp_employee_threshold INT DEFAULT 1, -- Min employees before required
  effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
  expires_at DATE,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_municipal_insurance_requirements_jurisdiction
  ON municipal_insurance_requirements(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_municipal_insurance_requirements_effective
  ON municipal_insurance_requirements(effective_date, expires_at);

-- Extend compliance_documents table with COI-specific fields
-- (Assumes compliance_documents table exists from previous migrations)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'compliance_documents'
    AND column_name = 'additional_insured_text'
  ) THEN
    ALTER TABLE compliance_documents
      ADD COLUMN additional_insured_text TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'compliance_documents'
    AND column_name = 'extracted_limits'
  ) THEN
    ALTER TABLE compliance_documents
      ADD COLUMN extracted_limits JSONB;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'compliance_documents'
    AND column_name = 'policy_effective_date'
  ) THEN
    ALTER TABLE compliance_documents
      ADD COLUMN policy_effective_date DATE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'compliance_documents'
    AND column_name = 'policy_expiration_date'
  ) THEN
    ALTER TABLE compliance_documents
      ADD COLUMN policy_expiration_date DATE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'compliance_documents'
    AND column_name = 'auto_parsed_at'
  ) THEN
    ALTER TABLE compliance_documents
      ADD COLUMN auto_parsed_at TIMESTAMPTZ;
  END IF;
END $$;

-- COI validation history (track each validation attempt)
CREATE TABLE IF NOT EXISTS coi_validations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL,                    -- REFERENCES compliance_documents(id)
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  validated_at TIMESTAMPTZ DEFAULT NOW(),
  validation_engine_version TEXT,
  passed BOOLEAN NOT NULL,
  failures JSONB,                               -- Array of failure reasons
  warnings JSONB,                               -- Array of warnings
  extracted_data JSONB,                         -- Full OCR/parsed data
  validated_by TEXT,                            -- User or 'system'
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_coi_validations_document ON coi_validations(document_id);
CREATE INDEX IF NOT EXISTS idx_coi_validations_jurisdiction ON coi_validations(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_coi_validations_validated_at ON coi_validations(validated_at);

-- Insurance policies (structured storage of parsed COI data)
CREATE TABLE IF NOT EXISTS insurance_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  maker_id UUID NOT NULL,                       -- The insured party
  document_id UUID,                             -- Link to COI document
  policy_type TEXT CHECK (policy_type IN (
    'general_liability',
    'products_completed_ops',
    'workers_compensation',
    'commercial_auto',
    'umbrella',
    'other'
  )) NOT NULL,
  carrier_name TEXT NOT NULL,
  policy_number TEXT NOT NULL,
  effective_date DATE NOT NULL,
  expiration_date DATE NOT NULL,
  coverage_amount_cents BIGINT NOT NULL,
  per_occurrence_cents BIGINT,
  aggregate_cents BIGINT,
  deductible_cents BIGINT,
  additional_insureds TEXT[],                   -- Array of additional insured names
  status TEXT CHECK (status IN ('active','expired','canceled','pending')) DEFAULT 'active',
  verified_at TIMESTAMPTZ,
  verified_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insurance_policies_maker ON insurance_policies(maker_id);
CREATE INDEX IF NOT EXISTS idx_insurance_policies_expiration ON insurance_policies(expiration_date);
CREATE INDEX IF NOT EXISTS idx_insurance_policies_status ON insurance_policies(status);
CREATE INDEX IF NOT EXISTS idx_insurance_policies_type ON insurance_policies(policy_type);

-- Insurance compliance status per maker per jurisdiction
CREATE TABLE IF NOT EXISTS maker_insurance_compliance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  maker_id UUID NOT NULL,
  jurisdiction_id TEXT REFERENCES jurisdictions(id) ON DELETE CASCADE,
  compliant BOOLEAN NOT NULL DEFAULT false,
  last_checked_at TIMESTAMPTZ DEFAULT NOW(),
  next_check_at TIMESTAMPTZ,                    -- Schedule re-validation
  missing_requirements JSONB,                   -- What's missing/insufficient
  expires_at TIMESTAMPTZ,                       -- Earliest policy expiration
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(maker_id, jurisdiction_id)
);

CREATE INDEX IF NOT EXISTS idx_maker_insurance_compliance_maker ON maker_insurance_compliance(maker_id);
CREATE INDEX IF NOT EXISTS idx_maker_insurance_compliance_jurisdiction ON maker_insurance_compliance(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_maker_insurance_compliance_expires_at ON maker_insurance_compliance(expires_at);

-- Comments
COMMENT ON TABLE municipal_insurance_requirements IS 'City-specific insurance minimums and additional insured rules';
COMMENT ON TABLE coi_validations IS 'History of COI validation attempts against city requirements';
COMMENT ON TABLE insurance_policies IS 'Parsed insurance policy data from COIs';
COMMENT ON TABLE maker_insurance_compliance IS 'Current insurance compliance status per maker per city';

-- Insert initial insurance requirements
INSERT INTO municipal_insurance_requirements (
  jurisdiction_id,
  liability_min_cents,
  aggregate_min_cents,
  additional_insured_legal_name,
  notes
) VALUES
  (
    'san_francisco',
    100000000,  -- $1M
    200000000,  -- $2M
    'City and County of San Francisco',
    'SF Health Code §6.15 requirements'
  ),
  (
    'portland',
    100000000,  -- $1M
    200000000,  -- $2M
    'City of Portland and Multnomah County',
    'Multnomah County commissary requirements'
  ),
  (
    'seattle',
    100000000,  -- $1M
    200000000,  -- $2M
    'City of Seattle and King County',
    'King County TFE/commissary requirements'
  )
ON CONFLICT DO NOTHING;
