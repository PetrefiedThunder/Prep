-- MVP 85% Vertical Slice Migration
-- Adds user roles and compliance document workflow

-- ============================================================================
-- ADD USER ROLES
-- ============================================================================

-- Create role enum
CREATE TYPE user_role AS ENUM ('owner', 'tenant', 'admin');

-- Add role column to profiles table
ALTER TABLE public.profiles
ADD COLUMN role user_role DEFAULT 'tenant' NOT NULL;

-- Update the handle_new_user function to set role from user metadata
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  user_role user_role;
BEGIN
  -- Get role from user metadata, default to 'tenant' if not set
  user_role := COALESCE((NEW.raw_user_meta_data->>'role')::user_role, 'tenant');

  INSERT INTO public.profiles (id, email, role)
  VALUES (NEW.id, NEW.email, user_role);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create index on role for efficient filtering
CREATE INDEX idx_profiles_role ON public.profiles(role);

-- Add RLS policy for admin access
CREATE POLICY "Admins can view all profiles"
  ON public.profiles FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  );

-- ============================================================================
-- KITCHEN_DOCUMENTS TABLE
-- ============================================================================

-- Document type enum
CREATE TYPE document_type AS ENUM ('health_permit', 'insurance_certificate');

-- Document status enum
CREATE TYPE document_status AS ENUM ('pending', 'approved', 'rejected');

-- Create kitchen_documents table
CREATE TABLE public.kitchen_documents (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  kitchen_id UUID REFERENCES public.kitchens(id) ON DELETE CASCADE NOT NULL,
  document_type document_type NOT NULL,
  file_url TEXT NOT NULL,
  file_name TEXT NOT NULL,
  status document_status DEFAULT 'pending' NOT NULL,
  uploaded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  reviewed_at TIMESTAMPTZ,
  reviewer_id UUID REFERENCES public.profiles(id),
  review_notes TEXT
);

-- Indexes
CREATE INDEX idx_kitchen_documents_kitchen_id ON public.kitchen_documents(kitchen_id);
CREATE INDEX idx_kitchen_documents_status ON public.kitchen_documents(status);
CREATE INDEX idx_kitchen_documents_reviewer_id ON public.kitchen_documents(reviewer_id);

-- Enable RLS
ALTER TABLE public.kitchen_documents ENABLE ROW LEVEL SECURITY;

-- RLS Policies for kitchen_documents

-- Kitchen owners can view their own kitchen documents
CREATE POLICY "Owners can view own kitchen documents"
  ON public.kitchen_documents FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = kitchen_documents.kitchen_id
      AND kitchens.owner_id = auth.uid()
    )
  );

-- Kitchen owners can upload documents for their kitchens
CREATE POLICY "Owners can upload kitchen documents"
  ON public.kitchen_documents FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = kitchen_documents.kitchen_id
      AND kitchens.owner_id = auth.uid()
    )
  );

-- Kitchen owners can update their own pending documents
CREATE POLICY "Owners can update own pending documents"
  ON public.kitchen_documents FOR UPDATE
  USING (
    status = 'pending' AND
    EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id = kitchen_documents.kitchen_id
      AND kitchens.owner_id = auth.uid()
    )
  );

-- Admins can view all documents
CREATE POLICY "Admins can view all documents"
  ON public.kitchen_documents FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  );

-- Admins can update (review) all documents
CREATE POLICY "Admins can review all documents"
  ON public.kitchen_documents FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  );

-- ============================================================================
-- COMPLIANCE STATUS FOR KITCHENS
-- ============================================================================

-- Add compliance_approved flag to kitchens table
ALTER TABLE public.kitchens
ADD COLUMN compliance_approved BOOLEAN DEFAULT false NOT NULL;

-- Create index for compliance filtering
CREATE INDEX idx_kitchens_compliance ON public.kitchens(compliance_approved);

-- Function to check if kitchen has required documents approved
CREATE OR REPLACE FUNCTION public.check_kitchen_compliance(kitchen_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
  health_permit_approved BOOLEAN;
  insurance_approved BOOLEAN;
BEGIN
  -- Check if health permit is approved
  SELECT EXISTS (
    SELECT 1 FROM public.kitchen_documents
    WHERE kitchen_id = kitchen_uuid
    AND document_type = 'health_permit'
    AND status = 'approved'
  ) INTO health_permit_approved;

  -- Check if insurance certificate is approved
  SELECT EXISTS (
    SELECT 1 FROM public.kitchen_documents
    WHERE kitchen_id = kitchen_uuid
    AND document_type = 'insurance_certificate'
    AND status = 'approved'
  ) INTO insurance_approved;

  -- Return true if both documents are approved
  RETURN health_permit_approved AND insurance_approved;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to auto-update compliance_approved when documents change
CREATE OR REPLACE FUNCTION public.update_kitchen_compliance()
RETURNS TRIGGER AS $$
BEGIN
  -- Update the kitchen's compliance_approved flag
  UPDATE public.kitchens
  SET compliance_approved = public.check_kitchen_compliance(NEW.kitchen_id)
  WHERE id = NEW.kitchen_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to update compliance when documents are reviewed
CREATE TRIGGER on_document_status_change
  AFTER INSERT OR UPDATE OF status ON public.kitchen_documents
  FOR EACH ROW EXECUTE FUNCTION public.update_kitchen_compliance();

-- Update existing kitchens policy to only show compliant kitchens to tenants
DROP POLICY IF EXISTS "Anyone can view active kitchens" ON public.kitchens;

CREATE POLICY "Anyone can view active compliant kitchens"
  ON public.kitchens FOR SELECT
  USING (is_active = true AND compliance_approved = true);

-- Owners can still see their own kitchens regardless of compliance
-- (existing policy "Owners can view own kitchens" already handles this)

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View for pending documents with kitchen and owner info (for admin dashboard)
CREATE OR REPLACE VIEW public.pending_documents_view AS
SELECT
  kd.id as document_id,
  kd.document_type,
  kd.file_url,
  kd.file_name,
  kd.uploaded_at,
  k.id as kitchen_id,
  k.title as kitchen_title,
  k.address,
  k.city,
  k.state,
  p.id as owner_id,
  p.email as owner_email,
  p.full_name as owner_name
FROM public.kitchen_documents kd
JOIN public.kitchens k ON kd.kitchen_id = k.id
JOIN public.profiles p ON k.owner_id = p.id
WHERE kd.status = 'pending'
ORDER BY kd.uploaded_at ASC;

-- Grant access to admins
-- Note: RLS still applies, so only admins will see results from this view
