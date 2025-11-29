-- Direct SQL seed script for demo data
-- Run this to populate the database with test data

BEGIN;

-- Insert test users (password is bcrypt hash of 'demo123')
INSERT INTO users (id, name, username, email, password_hash, full_name, role, verified, created_at, updated_at)
VALUES 
  ('11111111-1111-1111-1111-111111111111'::uuid, 'Demo Host', 'demo-host', 'host@prep.demo', '$2a$10$rKfWkZQZ.qJ9vYqnY8xQ7O5XJ5Z0qX5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5e', 'Demo Host', 'host', true, NOW(), NOW()),
  ('22222222-2222-2222-2222-222222222222'::uuid, 'Demo Renter', 'demo-renter', 'renter@prep.demo', '$2a$10$rKfWkZQZ.qJ9vYqnY8xQ7O5XJ5Z0qX5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5e', 'Demo Renter', 'renter', true, NOW(), NOW()),
  ('33333333-3333-3333-3333-333333333333'::uuid, 'Demo Admin', 'demo-admin', 'admin@prep.demo', '$2a$10$rKfWkZQZ.qJ9vYqnY8xQ7O5XJ5Z0qX5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5e', 'Demo Admin', 'admin', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Insert test business
INSERT INTO businesses (id, owner_id, name, legal_name, address, phone, email, verified, created_at, updated_at)
VALUES 
  ('44444444-4444-4444-4444-444444444444'::uuid, 
   '11111111-1111-1111-1111-111111111111'::uuid,
   'Harbor Kitchen SF',
   'Harbor Kitchen SF LLC',
   '{"street": "123 Market Street", "city": "San Francisco", "state": "CA", "zip": "94103", "country": "US"}'::jsonb,
   '+1-415-555-0100',
   'business@harborhomes.demo',
   true,
   NOW(),
   NOW())
ON CONFLICT DO NOTHING;

-- Insert test venue
INSERT INTO venues (id, business_id, name, address, timezone, created_at, updated_at)
VALUES 
  ('55555555-5555-5555-5555-555555555555'::uuid,
   '44444444-4444-4444-4444-444444444444'::uuid,
   'Harbor Kitchen SF - Main Location',
   '{"street": "123 Market Street", "city": "San Francisco", "state": "CA", "zip": "94103", "country": "US", "lat": 37.7749, "lng": -122.4194}'::jsonb,
   'America/Los_Angeles',
   NOW(),
   NOW())
ON CONFLICT DO NOTHING;

-- Insert test kitchen listings
INSERT INTO kitchen_listings (id, venue_id, title, description, kitchen_type, hourly_rate_cents, cleaning_fee_cents, is_active, is_featured, created_at, updated_at)
VALUES 
  ('66666666-6666-6666-6666-666666666666'::uuid,
   '55555555-5555-5555-5555-555555555555'::uuid,
   'Commercial Kitchen - Full Service',
   'Fully equipped commercial kitchen in the heart of San Francisco. Perfect for food trucks, caterers, and small batch producers.',
   ARRAY['commercial', 'prep']::TEXT[],
   5000, -- $50/hr
   2500, -- $25 cleaning fee
   true,
   true,
   NOW(),
   NOW()),
  ('77777777-7777-7777-7777-777777777777'::uuid,
   '55555555-5555-5555-5555-555555555555'::uuid,
   'Bakery Kitchen - Specialty',
   'Professional bakery space with commercial ovens, mixers, and proofing equipment. Ideal for bakers and pastry chefs.',
   ARRAY['bakery', 'baking']::TEXT[],
   6000, -- $60/hr
   2500,
   true,
   true,
   NOW(),
   NOW()),
  ('88888888-8888-8888-8888-888888888888'::uuid,
   '55555555-5555-5555-5555-555555555555'::uuid,
   'Prep Kitchen - Shared Space',
   'Shared prep kitchen with flexible scheduling. Great for meal prep, catering prep, and food product development.',
   ARRAY['prep', 'shared']::TEXT[],
   4000, -- $40/hr
   1500,
   true,
   false,
   NOW(),
   NOW())
ON CONFLICT DO NOTHING;

-- Insert availability windows for next 30 days (6am-12pm, 12pm-6pm, 6pm-12am slots)
DO $$
DECLARE
  listing_id UUID;
  day_date DATE;
BEGIN
  FOR listing_id IN SELECT id FROM kitchen_listings LOOP
    FOR day_date IN SELECT generate_series(CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', '1 day'::interval)::DATE LOOP
      -- Morning slot (6am-12pm)
      INSERT INTO availability_windows (listing_id, start_time, end_time, start_date, end_date, is_recurring)
      VALUES (listing_id, '06:00:00'::TIME, '12:00:00'::TIME, day_date, day_date, false)
      ON CONFLICT DO NOTHING;
      
      -- Afternoon slot (12pm-6pm)
      INSERT INTO availability_windows (listing_id, start_time, end_time, start_date, end_date, is_recurring)
      VALUES (listing_id, '12:00:00'::TIME, '18:00:00'::TIME, day_date, day_date, false)
      ON CONFLICT DO NOTHING;
      
      -- Evening slot (6pm-12am)
      INSERT INTO availability_windows (listing_id, start_time, end_time, start_date, end_date, is_recurring)
      VALUES (listing_id, '18:00:00'::TIME, '23:59:59'::TIME, day_date, day_date, false)
      ON CONFLICT DO NOTHING;
    END LOOP;
  END LOOP;
END $$;

-- Insert a sample completed booking
INSERT INTO bookings (
  id, 
  user_id,
  kitchen_id,
  listing_id, 
  renter_id, 
  start_time, 
  end_time, 
  status, 
  hourly_rate_cents,
  subtotal_cents,
  cleaning_fee_cents,
  service_fee_cents,
  tax_cents,
  total_cents,
  payment_status,
  guest_count,
  created_at, 
  updated_at
)
VALUES (
  '99999999-9999-9999-9999-999999999999'::uuid,
  '22222222-2222-2222-2222-222222222222'::uuid,
  '66666666-6666-6666-6666-666666666666'::uuid,
  '66666666-6666-6666-6666-666666666666'::uuid,
  '22222222-2222-2222-2222-222222222222'::uuid,
  (CURRENT_DATE - INTERVAL '7 days')::TIMESTAMP + TIME '10:00:00',
  (CURRENT_DATE - INTERVAL '7 days')::TIMESTAMP + TIME '16:00:00',
  'completed',
  5000,  -- $50/hr
  30000, -- 6 hours * $50
  2500,  -- cleaning fee
  3250,  -- service fee (10%)
  2700,  -- tax (8%)
  38450, -- total
  'captured',
  2,
  NOW() - INTERVAL '7 days',
  NOW() - INTERVAL '7 days'
)
ON CONFLICT DO NOTHING;

COMMIT;

-- Show summary
SELECT 
  'users' as table_name, 
  COUNT(*) as count 
FROM users
WHERE email LIKE '%@prep.demo'
UNION ALL
SELECT 'businesses', COUNT(*) FROM businesses
UNION ALL
SELECT 'venues', COUNT(*) FROM venues
UNION ALL
SELECT 'kitchen_listings', COUNT(*) FROM kitchen_listings
UNION ALL
SELECT 'availability_windows', COUNT(*) FROM availability_windows
UNION ALL
SELECT 'bookings', COUNT(*) FROM bookings;
