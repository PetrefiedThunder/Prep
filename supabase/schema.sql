-- PrepChef Database Schema
-- Run this in your Supabase SQL editor to set up the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PROFILES TABLE
-- ============================================================================
-- Extends Supabase auth.users with additional profile information
CREATE TABLE public.profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  phone TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Enable RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies for profiles
CREATE POLICY "Users can view own profile"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON public.profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

-- ============================================================================
-- KITCHENS TABLE
-- ============================================================================
CREATE TABLE public.kitchens (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  owner_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  address TEXT NOT NULL,
  city TEXT NOT NULL,
  state TEXT NOT NULL,
  zip_code TEXT NOT NULL,
  price_per_hour DECIMAL(10, 2) NOT NULL CHECK (price_per_hour >= 0),
  max_capacity INTEGER CHECK (max_capacity > 0),
  square_feet INTEGER,
  is_active BOOLEAN DEFAULT true NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_kitchens_owner_id ON public.kitchens(owner_id);
CREATE INDEX idx_kitchens_city ON public.kitchens(city);
CREATE INDEX idx_kitchens_is_active ON public.kitchens(is_active);

-- Enable RLS
ALTER TABLE public.kitchens ENABLE ROW LEVEL SECURITY;

-- RLS Policies for kitchens
CREATE POLICY "Anyone can view active kitchens"
  ON public.kitchens FOR SELECT
  USING (is_active = true);

CREATE POLICY "Owners can view own kitchens"
  ON public.kitchens FOR SELECT
  USING (auth.uid() = owner_id);

CREATE POLICY "Owners can insert own kitchens"
  ON public.kitchens FOR INSERT
  WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Owners can update own kitchens"
  ON public.kitchens FOR UPDATE
  USING (auth.uid() = owner_id);

CREATE POLICY "Owners can delete own kitchens"
  ON public.kitchens FOR DELETE
  USING (auth.uid() = owner_id);

-- ============================================================================
-- KITCHEN_PHOTOS TABLE
-- ============================================================================
CREATE TABLE public.kitchen_photos (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  kitchen_id UUID REFERENCES public.kitchens(id) ON DELETE CASCADE NOT NULL,
  url TEXT NOT NULL,
  is_primary BOOLEAN DEFAULT false NOT NULL,
  sort_order INTEGER DEFAULT 0 NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_kitchen_photos_kitchen_id ON public.kitchen_photos(kitchen_id);

-- Enable RLS
ALTER TABLE public.kitchen_photos ENABLE ROW LEVEL SECURITY;

-- RLS Policies for kitchen_photos
CREATE POLICY "Anyone can view photos of active kitchens"
  ON public.kitchen_photos FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = kitchen_photos.kitchen_id
      AND kitchens.is_active = true
    )
  );

CREATE POLICY "Kitchen owners can insert photos"
  ON public.kitchen_photos FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = kitchen_photos.kitchen_id
      AND kitchens.owner_id = auth.uid()
    )
  );

CREATE POLICY "Kitchen owners can update photos"
  ON public.kitchen_photos FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = kitchen_photos.kitchen_id
      AND kitchens.owner_id = auth.uid()
    )
  );

CREATE POLICY "Kitchen owners can delete photos"
  ON public.kitchen_photos FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = kitchen_photos.kitchen_id
      AND kitchens.owner_id = auth.uid()
    )
  );

-- ============================================================================
-- STRIPE_ACCOUNTS TABLE
-- ============================================================================
CREATE TABLE public.stripe_accounts (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
  stripe_account_id TEXT UNIQUE NOT NULL,
  onboarding_complete BOOLEAN DEFAULT false NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_stripe_accounts_user_id ON public.stripe_accounts(user_id);
CREATE INDEX idx_stripe_accounts_stripe_id ON public.stripe_accounts(stripe_account_id);

-- Enable RLS
ALTER TABLE public.stripe_accounts ENABLE ROW LEVEL SECURITY;

-- RLS Policies for stripe_accounts
CREATE POLICY "Users can view own stripe account"
  ON public.stripe_accounts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own stripe account"
  ON public.stripe_accounts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own stripe account"
  ON public.stripe_accounts FOR UPDATE
  USING (auth.uid() = user_id);

-- ============================================================================
-- BOOKINGS TABLE
-- ============================================================================
CREATE TYPE booking_status AS ENUM ('pending', 'confirmed', 'cancelled', 'completed');

CREATE TABLE public.bookings (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  kitchen_id UUID REFERENCES public.kitchens(id) ON DELETE CASCADE NOT NULL,
  renter_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  total_hours DECIMAL(10, 2) NOT NULL CHECK (total_hours > 0),
  price_per_hour DECIMAL(10, 2) NOT NULL CHECK (price_per_hour >= 0),
  total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
  status booking_status DEFAULT 'pending' NOT NULL,
  stripe_payment_intent_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT valid_time_range CHECK (end_time > start_time)
);

CREATE INDEX idx_bookings_kitchen_id ON public.bookings(kitchen_id);
CREATE INDEX idx_bookings_renter_id ON public.bookings(renter_id);
CREATE INDEX idx_bookings_start_time ON public.bookings(start_time);
CREATE INDEX idx_bookings_status ON public.bookings(status);

-- Enable RLS
ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for bookings
CREATE POLICY "Renters can view own bookings"
  ON public.bookings FOR SELECT
  USING (auth.uid() = renter_id);

CREATE POLICY "Kitchen owners can view bookings for their kitchens"
  ON public.bookings FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = bookings.kitchen_id
      AND kitchens.owner_id = auth.uid()
    )
  );

CREATE POLICY "Users can create bookings"
  ON public.bookings FOR INSERT
  WITH CHECK (auth.uid() = renter_id);

CREATE POLICY "Renters can update own bookings"
  ON public.bookings FOR UPDATE
  USING (auth.uid() = renter_id);

-- ============================================================================
-- PAYOUTS TABLE
-- ============================================================================
CREATE TYPE payout_status AS ENUM ('pending', 'processing', 'paid', 'failed');

CREATE TABLE public.payouts (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  booking_id UUID REFERENCES public.bookings(id) ON DELETE CASCADE UNIQUE NOT NULL,
  owner_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
  platform_fee DECIMAL(10, 2) DEFAULT 0 NOT NULL CHECK (platform_fee >= 0),
  net_amount DECIMAL(10, 2) NOT NULL CHECK (net_amount >= 0),
  status payout_status DEFAULT 'pending' NOT NULL,
  stripe_transfer_id TEXT,
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_payouts_booking_id ON public.payouts(booking_id);
CREATE INDEX idx_payouts_owner_id ON public.payouts(owner_id);
CREATE INDEX idx_payouts_status ON public.payouts(status);

-- Enable RLS
ALTER TABLE public.payouts ENABLE ROW LEVEL SECURITY;

-- RLS Policies for payouts
CREATE POLICY "Owners can view own payouts"
  ON public.payouts FOR SELECT
  USING (auth.uid() = owner_id);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to automatically create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to call handle_new_user
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all relevant tables
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_kitchens_updated_at BEFORE UPDATE ON public.kitchens
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_stripe_accounts_updated_at BEFORE UPDATE ON public.stripe_accounts
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_bookings_updated_at BEFORE UPDATE ON public.bookings
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_payouts_updated_at BEFORE UPDATE ON public.payouts
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
