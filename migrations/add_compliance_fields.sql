-- Add compliance fields to kitchens table
ALTER TABLE kitchens 
ADD COLUMN IF NOT EXISTS compliance_status VARCHAR(20) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS risk_score INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_compliance_check TIMESTAMP,
ADD COLUMN IF NOT EXISTS state VARCHAR(2),
ADD COLUMN IF NOT EXISTS city VARCHAR(100),
ADD COLUMN IF NOT EXISTS health_permit_number VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_inspection_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS insurance_info JSONB,
ADD COLUMN IF NOT EXISTS zoning_type VARCHAR(50);

-- Create index for compliance filtering
CREATE INDEX IF NOT EXISTS idx_kitchens_compliance ON kitchens(compliance_status, state, city);
CREATE INDEX IF NOT EXISTS idx_kitchens_risk_score ON kitchens(risk_score);

-- Add regulatory tracking table
CREATE TABLE IF NOT EXISTS regulatory_updates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state VARCHAR(2) NOT NULL,
    city VARCHAR(100),
    regulation_type VARCHAR(100) NOT NULL,
    change_description TEXT NOT NULL,
    effective_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
