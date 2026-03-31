-- Migration: Photo Upload to Supabase Storage
-- Phase 2 Priority 1: Replace URL-based kitchen photos with file uploads
-- Date: 2026-03-31

-- ============================================================================
-- 1. Add storage_path column to kitchen_photos
-- ============================================================================
-- Tracks the Supabase Storage path for each photo, enabling deletion.
-- Nullable to support existing URL-only records.
ALTER TABLE public.kitchen_photos
  ADD COLUMN IF NOT EXISTS storage_path TEXT;

-- ============================================================================
-- 2. Create Supabase Storage bucket for kitchen photos
-- ============================================================================
-- Run this in Supabase Dashboard > Storage, or via the API:
--   Bucket name: kitchen-photos
--   Public: true (photos are publicly viewable)
--   File size limit: 5MB
--   Allowed MIME types: image/jpeg, image/png, image/webp
--
-- SQL to insert bucket (if using raw SQL):
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'kitchen-photos',
  'kitchen-photos',
  true,
  5242880,
  ARRAY['image/jpeg', 'image/png', 'image/webp']
)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 3. Storage RLS Policies
-- ============================================================================
-- Allow anyone to view kitchen photos (public bucket)
CREATE POLICY "Anyone can view kitchen photos"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'kitchen-photos');

-- Allow authenticated users to upload photos to their kitchen folders
-- The storage path format is: {kitchen_id}/{filename}
-- We verify the user owns the kitchen referenced by the folder name
CREATE POLICY "Kitchen owners can upload photos"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'kitchen-photos'
    AND auth.role() = 'authenticated'
    AND EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id::text = (storage.foldername(name))[1]
      AND kitchens.owner_id = auth.uid()
    )
  );

-- Allow kitchen owners to delete their photos
CREATE POLICY "Kitchen owners can delete photos"
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'kitchen-photos'
    AND auth.role() = 'authenticated'
    AND EXISTS (
      SELECT 1 FROM public.kitchens
      WHERE kitchens.id::text = (storage.foldername(name))[1]
      AND kitchens.owner_id = auth.uid()
    )
  );
