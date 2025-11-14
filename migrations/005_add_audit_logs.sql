-- Migration 005: Immutable audit logs (T56)
-- Creates audit_logs table for critical event tracking

BEGIN;

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  event_type VARCHAR(50) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  entity_id UUID NOT NULL,
  user_id UUID,
  changes JSONB,
  metadata JSONB,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Index for querying by entity
CREATE INDEX idx_audit_logs_entity ON audit_logs (entity_type, entity_id, created_at DESC);

-- Index for querying by user
CREATE INDEX idx_audit_logs_user ON audit_logs (user_id, created_at DESC);

-- Index for querying by event type
CREATE INDEX idx_audit_logs_event_type ON audit_logs (event_type, created_at DESC);

-- Prevent updates and deletes (immutable)
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Audit logs are immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_log_updates
  BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW
  EXECUTE FUNCTION prevent_audit_log_modification();

-- Create audit log function for bookings
CREATE OR REPLACE FUNCTION log_booking_change()
RETURNS TRIGGER AS $$
DECLARE
  changes_json JSONB;
BEGIN
  IF TG_OP = 'UPDATE' THEN
    changes_json = jsonb_build_object(
      'old', row_to_json(OLD),
      'new', row_to_json(NEW)
    );
  ELSIF TG_OP = 'INSERT' THEN
    changes_json = jsonb_build_object('new', row_to_json(NEW));
  ELSIF TG_OP = 'DELETE' THEN
    changes_json = jsonb_build_object('old', row_to_json(OLD));
  END IF;

  INSERT INTO audit_logs (
    event_type,
    entity_type,
    entity_id,
    user_id,
    changes
  ) VALUES (
    TG_OP,
    'booking',
    COALESCE(NEW.booking_id, OLD.booking_id),
    COALESCE(NEW.user_id, OLD.user_id),
    changes_json
  );

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_bookings_changes
  AFTER INSERT OR UPDATE OR DELETE ON bookings
  FOR EACH ROW
  EXECUTE FUNCTION log_booking_change();

COMMIT;
