-- Regulatory data tables
CREATE TABLE IF NOT EXISTS regulation_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state VARCHAR(2) NOT NULL,
    city VARCHAR(100),
    source_url TEXT NOT NULL,
    source_type VARCHAR(50),
    last_scraped TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS regulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES regulation_sources(id),
    regulation_type VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    requirements JSONB,
    applicable_to VARCHAR(50)[],
    effective_date TIMESTAMP,
    expiration_date TIMESTAMP,
    jurisdiction VARCHAR(100),
    citation VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS insurance_requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state VARCHAR(2) NOT NULL,
    city VARCHAR(100),
    minimum_coverage JSONB,
    required_policies VARCHAR(100)[],
    special_requirements TEXT,
    notes TEXT,
    source_url TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_regulations_state ON regulations(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_regulations_type ON regulations(regulation_type);
CREATE INDEX IF NOT EXISTS idx_insurance_state ON insurance_requirements(state);
