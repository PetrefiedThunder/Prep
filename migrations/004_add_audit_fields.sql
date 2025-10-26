-- Migration 004: Add created_by audit fields (Q49)
-- Adds audit tracking to listings and bookings tables

BEGIN;

-- Add created_by to listings table
ALTER TABLE IF EXISTS listings
  ADD COLUMN IF NOT EXISTS created_by UUID,
  ADD COLUMN IF NOT EXISTS updated_by UUID;

-- Add created_by to bookings table
ALTER TABLE IF EXISTS bookings
  ADD COLUMN IF NOT EXISTS created_by UUID,
  ADD COLUMN IF NOT EXISTS updated_by UUID;

-- Backfill with system user (create if doesn't exist)
DO $$
DECLARE
  system_user_id UUID;
BEGIN
  -- Create system user if not exists
  INSERT INTO users (user_id, email, name, role)
  VALUES (
    '00000000-0000-0000-0000-000000000001'::UUID,
    'system@prepchef.com',
    'System',
    'system'
  )
  ON CONFLICT (user_id) DO NOTHING;

  system_user_id := '00000000-0000-0000-0000-000000000001'::UUID;

  -- Backfill listings
  UPDATE listings
  SET created_by = system_user_id,
      updated_by = system_user_id
  WHERE created_by IS NULL;

  -- Backfill bookings
  UPDATE bookings
  SET created_by = system_user_id,
      updated_by = system_user_id
  WHERE created_by IS NULL;
END $$;

-- Create trigger to auto-update updated_by
CREATE OR REPLACE FUNCTION update_audit_fields()
RETURNS TRIGGER AS $$
BEGIN
  -- Set updated_by to current user (from application context)
  -- In practice, this would be set by the application
  NEW.updated_by = COALESCE(current_setting('app.current_user_id', true)::UUID, NEW.updated_by);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER listings_audit_trigger
  BEFORE UPDATE ON listings
  FOR EACH ROW
  EXECUTE FUNCTION update_audit_fields();

CREATE TRIGGER bookings_audit_trigger
  BEFORE UPDATE ON bookings
  FOR EACH ROW
  EXECUTE FUNCTION update_audit_fields();

COMMIT;
