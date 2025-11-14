-- Migration: Create bookings table with availability tracking
-- Version: 003
-- Date: 2025-01-26

BEGIN;

-- Create bookings table
CREATE TABLE IF NOT EXISTS bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kitchen_id UUID NOT NULL,
    user_id UUID NOT NULL,
    listing_id UUID,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'confirmed', 'cancelled', 'rejected')),
    payment_intent_id VARCHAR(255),
    amount_cents INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_time_range CHECK (start_time < end_time),
    CONSTRAINT future_booking CHECK (start_time > NOW())
);

-- Create index for availability checks (critical for performance)
CREATE INDEX idx_bookings_kitchen_time ON bookings (kitchen_id, start_time, end_time) WHERE status NOT IN ('cancelled', 'rejected');

-- Create index for start_time (for hold expiration worker)
CREATE INDEX idx_bookings_start_time ON bookings (start_time);

-- Create index for status and created_at (for pending booking cleanup)
CREATE INDEX idx_bookings_status_created ON bookings (status, created_at);

-- Create index for user bookings
CREATE INDEX idx_bookings_user_id ON bookings (user_id, created_at DESC);

-- Add trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION update_bookings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bookings_updated_at_trigger
    BEFORE UPDATE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION update_bookings_updated_at();

-- Create function to prevent overlapping bookings at database level
CREATE OR REPLACE FUNCTION check_booking_overlap()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM bookings
        WHERE kitchen_id = NEW.kitchen_id
          AND booking_id != COALESCE(NEW.booking_id, '00000000-0000-0000-0000-000000000000'::UUID)
          AND status NOT IN ('cancelled', 'rejected')
          AND (
              (start_time <= NEW.start_time AND end_time > NEW.start_time)
              OR (start_time < NEW.end_time AND end_time >= NEW.end_time)
              OR (start_time >= NEW.start_time AND end_time <= NEW.end_time)
          )
    ) THEN
        RAISE EXCEPTION 'Booking overlaps with existing booking';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_booking_overlap
    BEFORE INSERT OR UPDATE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION check_booking_overlap();

COMMIT;
