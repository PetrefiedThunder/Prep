-- PrepChef Commercial Kitchen Marketplace Database Schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "postgis"; -- For location-based queries

-- Custom types
CREATE TYPE user_role AS ENUM ('admin', 'host', 'renter', 'support');
CREATE TYPE booking_status AS ENUM (
    'requested',
    'awaiting_docs',
    'payment_authorized',
    'confirmed',
    'active',
    'completed',
    'canceled',
    'no_show',
    'disputed'
);
CREATE TYPE certification_type AS ENUM (
    'health_permit',
    'business_license',
    'food_handler',
    'insurance',
    'fire_safety'
);
CREATE TYPE document_status AS ENUM ('pending', 'approved', 'rejected', 'expired');
CREATE TYPE payment_status AS ENUM ('pending', 'authorized', 'captured', 'refunded', 'failed');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email CITEXT UNIQUE NOT NULL,
    username CITEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    role user_role NOT NULL DEFAULT 'renter',
    verified BOOLEAN DEFAULT FALSE,
    verification_token TEXT,
    verification_expires_at TIMESTAMPTZ,
    stripe_customer_id TEXT,
    stripe_connect_account_id TEXT, -- For hosts
    profile_data JSONB DEFAULT '{}',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Businesses table (for hosts)
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    legal_name TEXT NOT NULL,
    tax_id TEXT,
    address JSONB NOT NULL,
    phone TEXT NOT NULL,
    email CITEXT NOT NULL,
    website TEXT,
    description TEXT,
    logo_url TEXT,
    verified BOOLEAN DEFAULT FALSE,
    stripe_account_id TEXT,
    commission_rate DECIMAL(3,2) DEFAULT 0.20, -- Platform commission
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Venues table (physical locations)
CREATE TABLE venues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address JSONB NOT NULL,
    location GEOGRAPHY(POINT, 4326), -- PostGIS point for geo queries
    timezone TEXT NOT NULL DEFAULT 'America/Los_Angeles',
    phone TEXT,
    email CITEXT,
    capacity INTEGER,
    square_footage INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Kitchen listings
CREATE TABLE kitchen_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_id UUID NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    kitchen_type TEXT[], -- e.g., ['commercial', 'prep', 'baking']
    equipment JSONB DEFAULT '[]', -- Detailed equipment list
    certifications JSONB DEFAULT '[]',
    photos TEXT[] DEFAULT '{}',
    video_url TEXT,
    
    -- Pricing
    hourly_rate_cents INTEGER NOT NULL CHECK (hourly_rate_cents > 0),
    daily_rate_cents INTEGER,
    weekly_rate_cents INTEGER,
    monthly_rate_cents INTEGER,
    minimum_hours INTEGER DEFAULT 2,
    cleaning_fee_cents INTEGER DEFAULT 0,
    security_deposit_cents INTEGER DEFAULT 0,
    
    -- Availability rules
    advance_notice_hours INTEGER DEFAULT 24,
    max_booking_hours INTEGER DEFAULT 24,
    cancellation_policy JSONB,
    
    -- Features
    features TEXT[], -- e.g., ['walk-in-freezer', 'loading-dock', 'parking']
    restrictions TEXT[], -- e.g., ['no-meat', 'no-alcohol']
    accessibility_features TEXT[], -- e.g., ['wheelchair-accessible', 'ada-compliant']
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    average_rating DECIMAL(2,1),
    total_reviews INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Indexes for search
    CONSTRAINT valid_rating CHECK (average_rating >= 1 AND average_rating <= 5)
);

-- Availability windows
CREATE TABLE availability_windows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID NOT NULL REFERENCES kitchen_listings(id) ON DELETE CASCADE,
    day_of_week INTEGER CHECK (day_of_week >= 0 AND day_of_week <= 6), -- 0=Sunday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    start_date DATE,
    end_date DATE,
    is_recurring BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_time_range CHECK (end_time > start_time),
    CONSTRAINT valid_date_range CHECK (
        (start_date IS NULL AND end_date IS NULL) OR 
        (start_date IS NOT NULL AND end_date IS NOT NULL AND end_date >= start_date)
    )
);

-- Compliance documents
CREATE TABLE compliance_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('user', 'business', 'venue', 'listing')),
    entity_id UUID NOT NULL,
    document_type certification_type NOT NULL,
    document_url TEXT NOT NULL,
    document_number TEXT,
    issuing_authority TEXT,
    issue_date DATE,
    expiry_date DATE NOT NULL,
    status document_status DEFAULT 'pending',
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    rejection_reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_type, entity_id, document_type)
);

-- Bookings
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID NOT NULL REFERENCES kitchen_listings(id),
    renter_id UUID NOT NULL REFERENCES users(id),
    
    -- Time slots
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_hours DECIMAL(4,2) GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (end_time - start_time)) / 3600
    ) STORED,
    
    -- Status
    status booking_status NOT NULL DEFAULT 'requested',
    
    -- Pricing
    hourly_rate_cents INTEGER NOT NULL,
    subtotal_cents INTEGER NOT NULL,
    cleaning_fee_cents INTEGER DEFAULT 0,
    service_fee_cents INTEGER NOT NULL, -- Platform fee
    tax_cents INTEGER DEFAULT 0,
    total_cents INTEGER NOT NULL,
    security_deposit_cents INTEGER DEFAULT 0,
    
    -- Payment
    stripe_payment_intent_id TEXT,
    payment_status payment_status DEFAULT 'pending',
    paid_at TIMESTAMPTZ,
    
    -- Additional info
    guest_count INTEGER DEFAULT 1,
    purpose TEXT,
    special_requests TEXT,
    
    -- Cancellation
    canceled_by UUID REFERENCES users(id),
    canceled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    refund_amount_cents INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent double booking
    CONSTRAINT no_overlap EXCLUDE USING gist (
        listing_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status IN ('confirmed', 'active', 'completed')),
    
    CONSTRAINT valid_booking_time CHECK (end_time > start_time),
    CONSTRAINT valid_future_booking CHECK (start_time > NOW())
);

-- Access grants (for smart locks, etc.)
CREATE TABLE access_grants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    access_code TEXT NOT NULL,
    access_type TEXT NOT NULL DEFAULT 'pin', -- pin, qr_code, nfc
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    max_uses INTEGER,
    times_used INTEGER DEFAULT 0,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_access_period CHECK (valid_until > valid_from)
);

-- Reviews
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(id) UNIQUE,
    reviewer_id UUID NOT NULL REFERENCES users(id),
    listing_id UUID NOT NULL REFERENCES kitchen_listings(id),
    
    -- Ratings (1-5 scale)
    overall_rating INTEGER NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
    cleanliness_rating INTEGER CHECK (cleanliness_rating >= 1 AND cleanliness_rating <= 5),
    equipment_rating INTEGER CHECK (equipment_rating >= 1 AND equipment_rating <= 5),
    location_rating INTEGER CHECK (location_rating >= 1 AND location_rating <= 5),
    value_rating INTEGER CHECK (value_rating >= 1 AND value_rating <= 5),
    
    title TEXT,
    comment TEXT,
    photos TEXT[],
    
    -- Response from host
    host_response TEXT,
    host_responded_at TIMESTAMPTZ,
    
    is_verified BOOLEAN DEFAULT TRUE, -- Verified bookings only
    is_featured BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    sender_id UUID NOT NULL REFERENCES users(id),
    recipient_id UUID NOT NULL REFERENCES users(id),
    listing_id UUID REFERENCES kitchen_listings(id),
    booking_id UUID REFERENCES bookings(id),
    
    subject TEXT,
    body TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    
    attachments JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    CONSTRAINT different_users CHECK (sender_id != recipient_id)
);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    
    -- Delivery channels
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMPTZ,
    push_sent BOOLEAN DEFAULT FALSE,
    push_sent_at TIMESTAMPTZ,
    sms_sent BOOLEAN DEFAULT FALSE,
    sms_sent_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_role ON users(role) WHERE deleted_at IS NULL;
CREATE INDEX idx_businesses_owner ON businesses(owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_venues_business ON venues(business_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_venues_location ON venues USING GIST(location);
CREATE INDEX idx_listings_venue ON kitchen_listings(venue_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_listings_active ON kitchen_listings(is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_listings_featured ON kitchen_listings(is_featured) WHERE is_active = TRUE;
CREATE INDEX idx_listings_hourly_rate ON kitchen_listings(hourly_rate_cents) WHERE is_active = TRUE;
CREATE INDEX idx_availability_listing ON availability_windows(listing_id);
CREATE INDEX idx_bookings_listing ON bookings(listing_id);
CREATE INDEX idx_bookings_renter ON bookings(renter_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_start_time ON bookings(start_time);
CREATE INDEX idx_reviews_listing ON reviews(listing_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_recipient ON messages(recipient_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_notifications_user ON notifications(user_id) WHERE is_read = FALSE;
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_compliance_docs_entity ON compliance_documents(entity_type, entity_id);
CREATE INDEX idx_compliance_docs_expiry ON compliance_documents(expiry_date) WHERE status = 'approved';

-- Full text search
CREATE INDEX idx_listings_search ON kitchen_listings 
USING GIN(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Update triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    
CREATE TRIGGER update_businesses_updated_at BEFORE UPDATE ON businesses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    
CREATE TRIGGER update_venues_updated_at BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    
CREATE TRIGGER update_listings_updated_at BEFORE UPDATE ON kitchen_listings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    
CREATE TRIGGER update_bookings_updated_at BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    
CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Row Level Security (RLS) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Sample RLS policies (customize based on your auth system)
CREATE POLICY users_select_own ON users
    FOR SELECT USING (id = current_setting('app.user_id')::UUID OR role = 'admin');

CREATE POLICY bookings_select_own ON bookings
    FOR SELECT USING (
        renter_id = current_setting('app.user_id')::UUID OR
        listing_id IN (
            SELECT id FROM kitchen_listings WHERE venue_id IN (
                SELECT id FROM venues WHERE business_id IN (
                    SELECT id FROM businesses WHERE owner_id = current_setting('app.user_id')::UUID
                )
            )
        )
    );

CREATE MATERIALIZED VIEW listing_stats AS
SELECT
    l.id AS listing_id,
    COUNT(DISTINCT b.id) AS total_bookings,
    COUNT(DISTINCT b.renter_id) AS unique_renters,
    AVG(b.duration_hours) AS avg_booking_hours,
    SUM(b.total_cents) / 100.0 AS total_revenue,
    AVG(r.overall_rating) AS average_rating,
    COUNT(DISTINCT r.id) AS review_count
FROM kitchen_listings l
LEFT JOIN bookings b ON l.id = b.listing_id AND b.status = 'completed'
LEFT JOIN reviews r ON l.id = r.listing_id AND r.deleted_at IS NULL
GROUP BY l.id;

CREATE UNIQUE INDEX idx_listing_stats_id ON listing_stats(listing_id);

-- Materialized view for host performance metrics over the past 30 days
CREATE MATERIALIZED VIEW mv_host_metrics AS
WITH hosts AS (
    SELECT DISTINCT
        k.host_id
    FROM kitchens k
    WHERE k.host_id IS NOT NULL
), recent_bookings AS (
    SELECT
        k.host_id,
        SUM(b.total_amount) AS total_revenue_cents,
        COUNT(*) AS completed_shifts
    FROM bookings b
    JOIN kitchens k ON k.id = b.kitchen_id
    WHERE b.status = 'completed'
      AND b.end_time >= NOW() - INTERVAL '30 days'
    GROUP BY k.host_id
), recent_incidents AS (
    SELECT
        hi.host_id,
        COUNT(*) AS incident_count
    FROM host_incidents hi
    WHERE hi.occurred_at >= NOW() - INTERVAL '30 days'
    GROUP BY hi.host_id
)
SELECT
    h.host_id,
    COALESCE(rb.total_revenue_cents, 0) AS total_revenue_cents,
    COALESCE(rb.completed_shifts, 0) AS completed_shifts,
    COALESCE(ri.incident_count, 0) AS incident_count,
    NOW() AS calculated_at
FROM hosts h
LEFT JOIN recent_bookings rb ON h.host_id = rb.host_id
LEFT JOIN recent_incidents ri ON h.host_id = ri.host_id;

CREATE UNIQUE INDEX idx_mv_host_metrics_host_id ON mv_host_metrics(host_id);

-- Refresh materialized view function
CREATE OR REPLACE FUNCTION refresh_listing_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY listing_stats;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust based on your users)
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;
CREATE POLICY users_select_own ON
