'use server'

import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import type { KitchenFormData } from '@/lib/types'
import { sanitizeKitchenPayload } from '@/middleware/request_validation'

export async function createKitchen(data: KitchenFormData) {
  const supabase = await createClient()

  const cleanData = sanitizeKitchenPayload(data)

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: kitchen, error } = await supabase
    .from('kitchens')
    .insert({
      owner_id: user.id,
      title: cleanData.title,
      description: cleanData.description,
      address: cleanData.address,
      city: cleanData.city,
      state: cleanData.state,
      zip_code: cleanData.zip_code,
      price_per_hour: cleanData.price_per_hour,
      max_capacity: cleanData.max_capacity,
      square_feet: cleanData.square_feet || null,
      is_active: true,
    })
    .select()
    .single()

  if (error) {
    return { error: error.message }
  }

  revalidatePath('/owner/kitchens')
  return { data: kitchen }
}

export async function updateKitchen(id: string, data: KitchenFormData) {
  const supabase = await createClient()

  const cleanData = sanitizeKitchenPayload(data)

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: kitchen, error } = await supabase
    .from('kitchens')
    .update({
      title: cleanData.title,
      description: cleanData.description,
      address: cleanData.address,
      city: cleanData.city,
      state: cleanData.state,
      zip_code: cleanData.zip_code,
      price_per_hour: cleanData.price_per_hour,
      max_capacity: cleanData.max_capacity,
      square_feet: cleanData.square_feet || null,
    })
    .eq('id', id)
    .eq('owner_id', user.id)
    .select()
    .single()

  if (error) {
    return { error: error.message }
  }

  revalidatePath('/owner/kitchens')
  revalidatePath(`/kitchens/${id}`)
  return { data: kitchen }
}

export async function toggleKitchenActive(id: string, isActive: boolean) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { error } = await supabase
    .from('kitchens')
    .update({ is_active: isActive })
    .eq('id', id)
    .eq('owner_id', user.id)

  if (error) {
    return { error: error.message }
  }

  revalidatePath('/owner/kitchens')
  revalidatePath(`/kitchens/${id}`)
  return { success: true }
}

export async function deleteKitchen(id: string) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { error } = await supabase
    .from('kitchens')
    .delete()
    .eq('id', id)
    .eq('owner_id', user.id)

  if (error) {
    return { error: error.message }
  }

  revalidatePath('/owner/kitchens')
  return { success: true }
}

export async function getOwnerKitchens() {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: kitchens, error } = await supabase
    .from('kitchens')
    .select(`
      *,
      kitchen_photos (*)
    `)
    .eq('owner_id', user.id)
    .order('created_at', { ascending: false })

  if (error) {
    return { error: error.message }
  }

  return { data: kitchens }
}

export async function getKitchen(id: string) {
  const supabase = await createClient()

  const { data: kitchen, error } = await supabase
    .from('kitchens')
    .select(`
      *,
      kitchen_photos (*),
      profiles (email, full_name)
    `)
    .eq('id', id)
    .single()

  if (error) {
    return { error: error.message }
  }

  return { data: kitchen }
}
