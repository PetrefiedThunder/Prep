'use server'

import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import { logInfo, logError } from '@/lib/logger'

const BUCKET_NAME = 'kitchen-photos'
const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

/**
 * Upload a kitchen photo to Supabase Storage and create a database record.
 * Accepts FormData with 'file' and 'kitchenId' fields.
 */
export async function uploadKitchenPhoto(formData: FormData) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return { error: 'Unauthorized' }
  }

  const file = formData.get('file') as File | null
  const kitchenId = formData.get('kitchenId') as string | null

  if (!file || !kitchenId) {
    return { error: 'File and kitchen ID are required' }
  }

  // Validate file type
  if (!ALLOWED_TYPES.includes(file.type)) {
    return { error: 'Invalid file type. Allowed: JPEG, PNG, WebP' }
  }

  // Validate file size
  if (file.size > MAX_FILE_SIZE) {
    return { error: 'File too large. Maximum size is 5MB' }
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

  // Generate unique file path
  const fileExt = file.name.split('.').pop()?.toLowerCase() || 'jpg'
  const storagePath = `${kitchenId}/${Date.now()}-${Math.random().toString(36).substring(2, 8)}.${fileExt}`

  // Upload to Supabase Storage
  const { data: uploadData, error: uploadError } = await supabase.storage
    .from(BUCKET_NAME)
    .upload(storagePath, file, {
      cacheControl: '3600',
      upsert: false,
    })

  if (uploadError) {
    logError('Photo upload failed', { error: uploadError.message, kitchenId })
    return { error: `Upload failed: ${uploadError.message}` }
  }

  // Get public URL
  const { data: { publicUrl } } = supabase.storage
    .from(BUCKET_NAME)
    .getPublicUrl(uploadData.path)

  // Check if this is the first photo (make it primary)
  const { count } = await supabase
    .from('kitchen_photos')
    .select('*', { count: 'exact', head: true })
    .eq('kitchen_id', kitchenId)

  const isFirst = (count ?? 0) === 0

  // Create database record
  const { data: photo, error: dbError } = await supabase
    .from('kitchen_photos')
    .insert({
      kitchen_id: kitchenId,
      url: publicUrl,
      storage_path: uploadData.path,
      is_primary: isFirst,
      sort_order: count ?? 0,
    })
    .select()
    .single()

  if (dbError) {
    // Clean up uploaded file if DB insert fails
    await supabase.storage.from(BUCKET_NAME).remove([uploadData.path])
    logError('Photo DB insert failed', { error: dbError.message, kitchenId })
    return { error: dbError.message }
  }

  logInfo('Kitchen photo uploaded', { kitchenId, photoId: photo.id })
  revalidatePath(`/owner/kitchens`)
  revalidatePath(`/kitchens`)
  revalidatePath(`/kitchens/${kitchenId}`)
  return { data: photo }
}

/**
 * Delete a kitchen photo from storage and database.
 */
export async function deleteKitchenPhoto(photoId: string) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Get photo record with kitchen ownership check
  const { data: photo } = await supabase
    .from('kitchen_photos')
    .select('*, kitchens!inner(owner_id)')
    .eq('id', photoId)
    .single()

  if (!photo) {
    return { error: 'Photo not found' }
  }

  const kitchen = photo.kitchens as { owner_id: string }
  if (kitchen.owner_id !== user.id) {
    return { error: 'Unauthorized: You do not own this kitchen' }
  }

  // Delete from storage if storage_path exists
  if (photo.storage_path) {
    const { error: storageError } = await supabase.storage
      .from(BUCKET_NAME)
      .remove([photo.storage_path])

    if (storageError) {
      logError('Photo storage delete failed', { error: storageError.message, photoId })
    }
  }

  // Delete database record
  const { error: dbError } = await supabase
    .from('kitchen_photos')
    .delete()
    .eq('id', photoId)

  if (dbError) {
    return { error: dbError.message }
  }

  // If deleted photo was primary, make the next one primary
  if (photo.is_primary) {
    const { data: nextPhoto } = await supabase
      .from('kitchen_photos')
      .select('id')
      .eq('kitchen_id', photo.kitchen_id)
      .order('sort_order', { ascending: true })
      .limit(1)
      .single()

    if (nextPhoto) {
      await supabase
        .from('kitchen_photos')
        .update({ is_primary: true })
        .eq('id', nextPhoto.id)
    }
  }

  logInfo('Kitchen photo deleted', { photoId, kitchenId: photo.kitchen_id })
  revalidatePath(`/owner/kitchens`)
  revalidatePath(`/kitchens`)
  revalidatePath(`/kitchens/${photo.kitchen_id}`)
  return { success: true }
}

/**
 * Set a photo as the primary photo for a kitchen.
 */
export async function setPhotoAsPrimary(photoId: string) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Get photo with kitchen ownership check
  const { data: photo } = await supabase
    .from('kitchen_photos')
    .select('*, kitchens!inner(owner_id)')
    .eq('id', photoId)
    .single()

  if (!photo) {
    return { error: 'Photo not found' }
  }

  const kitchen = photo.kitchens as { owner_id: string }
  if (kitchen.owner_id !== user.id) {
    return { error: 'Unauthorized: You do not own this kitchen' }
  }

  // Unset current primary
  await supabase
    .from('kitchen_photos')
    .update({ is_primary: false })
    .eq('kitchen_id', photo.kitchen_id)
    .eq('is_primary', true)

  // Set new primary
  const { error } = await supabase
    .from('kitchen_photos')
    .update({ is_primary: true })
    .eq('id', photoId)

  if (error) {
    return { error: error.message }
  }

  revalidatePath(`/owner/kitchens`)
  revalidatePath(`/kitchens`)
  revalidatePath(`/kitchens/${photo.kitchen_id}`)
  return { success: true }
}

/**
 * Get all photos for a kitchen (for owner management).
 */
export async function getKitchenPhotos(kitchenId: string) {
  const supabase = await createClient()

  const { data: photos, error } = await supabase
    .from('kitchen_photos')
    .select('*')
    .eq('kitchen_id', kitchenId)
    .order('sort_order', { ascending: true })

  if (error) {
    return { error: error.message }
  }

  return { data: photos }
}
