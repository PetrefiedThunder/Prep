CREATE TABLE IF NOT EXISTS pos_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kitchen_id UUID NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL,
    merchant_id VARCHAR(128),
    location_identifier VARCHAR(128),
    access_token VARCHAR(255),
    refresh_token VARCHAR(255),
    expires_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (kitchen_id, provider)
);

CREATE TABLE IF NOT EXISTS pos_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id UUID NOT NULL REFERENCES pos_integrations(id) ON DELETE CASCADE,
    kitchen_id UUID NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL,
    location_id VARCHAR(120),
    external_id VARCHAR(120) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    occurred_at TIMESTAMPTZ NOT NULL,
    raw_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS ix_pos_transactions_kitchen_occurred_at
    ON pos_transactions (kitchen_id, occurred_at);

CREATE TABLE IF NOT EXISTS pos_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id UUID REFERENCES pos_integrations(id) ON DELETE SET NULL,
    kitchen_id UUID NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL,
    external_id VARCHAR(120) NOT NULL,
    order_number VARCHAR(120),
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    guest_count INTEGER,
    raw_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS ix_pos_orders_kitchen_closed_at
    ON pos_orders (kitchen_id, closed_at);
