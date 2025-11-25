-- Migration to align database with Prisma schema
-- Generated from prepchef/prisma/schema.prisma

-- Create CITEXT extension if not exists
CREATE EXTENSION IF NOT EXISTS citext;

-- Create enums
DO $$ BEGIN
    CREATE TYPE "UserRole" AS ENUM ('admin', 'host', 'renter', 'support');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE "BookingStatus" AS ENUM ('requested', 'awaiting_docs', 'payment_authorized', 'confirmed', 'active', 'completed', 'canceled', 'no_show', 'disputed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE "CertificationType" AS ENUM ('health_permit', 'business_license', 'food_handler', 'insurance', 'fire_safety');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE "DocumentStatus" AS ENUM ('pending', 'approved', 'rejected', 'expired');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE "PaymentStatus" AS ENUM ('pending', 'authorized', 'captured', 'refunded', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Alter users table to match Prisma schema
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS username CITEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS phone VARCHAR(50),
    ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255),
    ADD COLUMN IF NOT EXISTS verification_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS stripe_connect_account_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS profile_data JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Update email column to CITEXT if not already
DO $$ BEGIN
    ALTER TABLE users ALTER COLUMN email TYPE CITEXT;
EXCEPTION
    WHEN others THEN null;
END $$;

-- Create businesses table
CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255) NOT NULL,
    tax_id VARCHAR(50),
    address JSONB NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email CITEXT NOT NULL,
    website VARCHAR(500),
    description TEXT,
    logo_url VARCHAR(500),
    verified BOOLEAN DEFAULT false,
    stripe_account_id VARCHAR(255),
    commission_rate DECIMAL(3,2) DEFAULT 0.20,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Create venues table
CREATE TABLE IF NOT EXISTS venues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address JSONB NOT NULL,
    location TEXT,
    timezone VARCHAR(100) DEFAULT 'America/Los_Angeles',
    phone VARCHAR(50),
    email CITEXT,
    capacity INTEGER,
    square_footage INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Create kitchen_listings table
CREATE TABLE IF NOT EXISTS kitchen_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_id UUID NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    kitchen_type TEXT[],
    equipment JSONB DEFAULT '[]',
    certifications JSONB DEFAULT '[]',
    photos TEXT[] DEFAULT ARRAY[]::TEXT[],
    video_url VARCHAR(500),
    
    -- Pricing
    hourly_rate_cents INTEGER NOT NULL,
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
    features TEXT[] DEFAULT ARRAY[]::TEXT[],
    restrictions TEXT[] DEFAULT ARRAY[]::TEXT[],
    accessibility_features TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    average_rating DECIMAL(2,1),
    total_reviews INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Create availability_windows table
CREATE TABLE IF NOT EXISTS availability_windows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID NOT NULL REFERENCES kitchen_listings(id) ON DELETE CASCADE,
    day_of_week INTEGER,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    start_date DATE,
    end_date DATE,
    is_recurring BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Update bookings table to match Prisma schema
ALTER TABLE bookings 
    ADD COLUMN IF NOT EXISTS listing_id UUID,
    ADD COLUMN IF NOT EXISTS renter_id UUID,
    ADD COLUMN IF NOT EXISTS hourly_rate_cents INTEGER,
    ADD COLUMN IF NOT EXISTS subtotal_cents INTEGER,
    ADD COLUMN IF NOT EXISTS cleaning_fee_cents INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS service_fee_cents INTEGER,
    ADD COLUMN IF NOT EXISTS tax_cents INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_cents INTEGER,
    ADD COLUMN IF NOT EXISTS security_deposit_cents INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS guest_count INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS purpose TEXT,
    ADD COLUMN IF NOT EXISTS special_requests TEXT,
    ADD COLUMN IF NOT EXISTS canceled_by UUID,
    ADD COLUMN IF NOT EXISTS canceled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cancellation_reason TEXT,
    ADD COLUMN IF NOT EXISTS refund_amount_cents INTEGER,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Create access_grants table
CREATE TABLE IF NOT EXISTS access_grants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    access_code VARCHAR(50) NOT NULL,
    access_type VARCHAR(50) DEFAULT 'pin',
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    max_uses INTEGER,
    times_used INTEGER DEFAULT 0,
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Update reviews table
ALTER TABLE reviews 
    ADD COLUMN IF NOT EXISTS booking_id UUID UNIQUE,
    ADD COLUMN IF NOT EXISTS reviewer_id UUID,
    ADD COLUMN IF NOT EXISTS listing_id UUID,
    ADD COLUMN IF NOT EXISTS overall_rating INTEGER,
    ADD COLUMN IF NOT EXISTS cleanliness_rating INTEGER,
    ADD COLUMN IF NOT EXISTS equipment_rating INTEGER,
    ADD COLUMN IF NOT EXISTS location_rating INTEGER,
    ADD COLUMN IF NOT EXISTS value_rating INTEGER,
    ADD COLUMN IF NOT EXISTS title VARCHAR(255),
    ADD COLUMN IF NOT EXISTS photos TEXT[] DEFAULT ARRAY[]::TEXT[],
    ADD COLUMN IF NOT EXISTS host_response TEXT,
    ADD COLUMN IF NOT EXISTS host_responded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS helpful_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    sender_id UUID NOT NULL REFERENCES users(id),
    recipient_id UUID NOT NULL REFERENCES users(id),
    listing_id UUID REFERENCES kitchen_listings(id),
    booking_id UUID REFERENCES bookings(id),
    subject VARCHAR(500),
    body TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    attachments JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    email_sent BOOLEAN DEFAULT false,
    email_sent_at TIMESTAMPTZ,
    push_sent BOOLEAN DEFAULT false,
    push_sent_at TIMESTAMPTZ,
    sms_sent BOOLEAN DEFAULT false,
    sms_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create integrations table
CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kitchen_id UUID REFERENCES kitchen_listings(id),
    service_type VARCHAR(100) NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    auth_method VARCHAR(100) NOT NULL,
    sync_frequency VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS integrations_user_id_idx ON integrations(user_id);
CREATE INDEX IF NOT EXISTS integrations_kitchen_id_idx ON integrations(kitchen_id);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create stripe_webhook_events table
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add foreign key constraints to bookings if not exist
DO $$ BEGIN
    ALTER TABLE bookings ADD CONSTRAINT bookings_listing_id_fkey 
        FOREIGN KEY (listing_id) REFERENCES kitchen_listings(id);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    ALTER TABLE bookings ADD CONSTRAINT bookings_renter_id_fkey 
        FOREIGN KEY (renter_id) REFERENCES users(id);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    ALTER TABLE bookings ADD CONSTRAINT bookings_canceled_by_fkey 
        FOREIGN KEY (canceled_by) REFERENCES users(id);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add foreign key constraints to reviews if not exist
DO $$ BEGIN
    ALTER TABLE reviews ADD CONSTRAINT reviews_booking_id_fkey 
        FOREIGN KEY (booking_id) REFERENCES bookings(id);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    ALTER TABLE reviews ADD CONSTRAINT reviews_reviewer_id_fkey 
        FOREIGN KEY (reviewer_id) REFERENCES users(id);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    ALTER TABLE reviews ADD CONSTRAINT reviews_listing_id_fkey 
        FOREIGN KEY (listing_id) REFERENCES kitchen_listings(id);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Update compliance_documents to match schema if needed
ALTER TABLE compliance_documents 
    ADD COLUMN IF NOT EXISTS entity_type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS entity_id UUID,
    ADD COLUMN IF NOT EXISTS document_type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS document_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS document_number VARCHAR(255),
    ADD COLUMN IF NOT EXISTS issuing_authority VARCHAR(255),
    ADD COLUMN IF NOT EXISTS issue_date DATE,
    ADD COLUMN IF NOT EXISTS expiry_date DATE,
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

COMMENT ON TABLE businesses IS 'Business entities that own venues';
COMMENT ON TABLE venues IS 'Physical locations with kitchen facilities';
COMMENT ON TABLE kitchen_listings IS 'Bookable kitchen spaces within venues';
COMMENT ON TABLE availability_windows IS 'Time windows when listings are available';
