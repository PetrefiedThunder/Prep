import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import LogoutButton from './LogoutButton'

export default async function ProfilePage() {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return (
    <div className="max-w-2xl mx-auto mt-12">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          Your Profile
        </h1>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <p className="text-gray-900 font-medium">{user.email}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              User ID
            </label>
            <p className="text-gray-600 font-mono text-sm">{user.id}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Confirmed
            </label>
            <p className="text-gray-900">
              {user.email_confirmed_at ? (
                <span className="text-green-600">✓ Confirmed</span>
              ) : (
                <span className="text-yellow-600">⚠ Not confirmed</span>
              )}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Account Created
            </label>
            <p className="text-gray-900">
              {new Date(user.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t">
          <LogoutButton />
        </div>
      </div>
    </div>
  )
}
