'use server'

import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import type { DocumentType, DocumentStatus, KitchenDocument } from '@/lib/types'

/**
 * Upload a compliance document for a kitchen
 * This should be called after file upload to Supabase Storage
 */
export async function createKitchenDocument(
  kitchenId: string,
  documentType: DocumentType,
  fileUrl: string,
  fileName: string
) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Verify user owns this kitchen
  const { data: kitchen } = await supabase
    .from('kitchens')
    .select('owner_id')
    .eq('id', kitchenId)
    .single()

  if (!kitchen || kitchen.owner_id !== user.id) {
    return { error: 'Unauthorized: You do not own this kitchen' }
  }

  const { data: document, error } = await supabase
    .from('kitchen_documents')
    .insert({
      kitchen_id: kitchenId,
      document_type: documentType,
      file_url: fileUrl,
      file_name: fileName,
      status: 'pending',
    })
    .select()
    .single()

  if (error) {
    return { error: error.message }
  }

  revalidatePath(`/owner/kitchens/${kitchenId}`)
  revalidatePath('/admin/compliance')
  return { data: document }
}

/**
 * Get all documents for a specific kitchen (for owners)
 */
export async function getKitchenDocuments(kitchenId: string) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: documents, error } = await supabase
    .from('kitchen_documents')
    .select('*')
    .eq('kitchen_id', kitchenId)
    .order('uploaded_at', { ascending: false })

  if (error) {
    return { error: error.message }
  }

  return { data: documents }
}

/**
 * Get all pending documents for admin review
 */
export async function getPendingDocuments() {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Check if user is admin
  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()

  if (!profile || profile.role !== 'admin') {
    return { error: 'Unauthorized: Admin access required' }
  }

  // Query the pending_documents_view which joins kitchen and owner info
  const { data: documents, error } = await supabase
    .from('kitchen_documents')
    .select(`
      *,
      kitchens (
        title,
        address,
        city,
        state,
        profiles (
          email,
          full_name
        )
      )
    `)
    .eq('status', 'pending')
    .order('uploaded_at', { ascending: true })

  if (error) {
    return { error: error.message }
  }

  return { data: documents }
}

/**
 * Review (approve/reject) a compliance document
 */
export async function reviewDocument(
  documentId: string,
  status: 'approved' | 'rejected',
  reviewNotes?: string
) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Check if user is admin
  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()

  if (!profile || profile.role !== 'admin') {
    return { error: 'Unauthorized: Admin access required' }
  }

  // Get the document to find its kitchen_id
  const { data: document } = await supabase
    .from('kitchen_documents')
    .select('kitchen_id')
    .eq('id', documentId)
    .single()

  if (!document) {
    return { error: 'Document not found' }
  }

  // Update document status
  const { error } = await supabase
    .from('kitchen_documents')
    .update({
      status: status,
      reviewer_id: user.id,
      reviewed_at: new Date().toISOString(),
      review_notes: reviewNotes || null,
    })
    .eq('id', documentId)

  if (error) {
    return { error: error.message }
  }

  // Revalidate relevant pages
  revalidatePath('/admin/compliance')
  revalidatePath(`/owner/kitchens/${document.kitchen_id}`)
  return { success: true }
}

/**
 * Get document statistics for a kitchen
 */
export async function getKitchenComplianceStatus(kitchenId: string) {
  const supabase = await createClient()

  const { data: documents, error } = await supabase
    .from('kitchen_documents')
    .select('document_type, status')
    .eq('kitchen_id', kitchenId)

  if (error) {
    return { error: error.message }
  }

  const healthPermit = documents?.find(d => d.document_type === 'health_permit')
  const insurance = documents?.find(d => d.document_type === 'insurance_certificate')

  return {
    data: {
      health_permit_status: healthPermit?.status || 'missing',
      insurance_status: insurance?.status || 'missing',
      is_compliant: healthPermit?.status === 'approved' && insurance?.status === 'approved',
    }
  }
}

/**
 * Upload file to Supabase Storage
 */
export async function uploadDocumentFile(
  file: File,
  kitchenId: string,
  documentType: DocumentType
) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Generate unique file name
  const fileExt = file.name.split('.').pop()
  const fileName = `${kitchenId}/${documentType}-${Date.now()}.${fileExt}`

  // Upload to Supabase Storage
  const { data, error } = await supabase.storage
    .from('kitchen-documents')
    .upload(fileName, file, {
      cacheControl: '3600',
      upsert: false,
    })

  if (error) {
    return { error: error.message }
  }

  // Get public URL
  const { data: { publicUrl } } = supabase.storage
    .from('kitchen-documents')
    .getPublicUrl(data.path)

  return {
    data: {
      file_url: publicUrl,
      file_name: file.name,
    }
  }
}
