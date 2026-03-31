import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import KitchenEditForm from './KitchenEditForm'

interface EditKitchenPageProps {
  params: Promise<{ id: string }>
}

export default async function EditKitchenPage({ params }: EditKitchenPageProps) {
  const { id } = await params
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    redirect('/auth/login')
  }

  const { data: kitchen, error } = await supabase
    .from('kitchens')
    .select(`
      *,
      kitchen_photos (*)
    `)
    .eq('id', id)
    .eq('owner_id', user.id)
    .single()

  if (error || !kitchen) {
    redirect('/owner/kitchens')
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">
        Edit Kitchen
      </h1>
      <KitchenEditForm kitchen={kitchen} />
    </div>
  )
}
