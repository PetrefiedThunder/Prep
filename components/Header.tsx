import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'

export default async function Header() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  return (
    <header className="bg-gray-900 text-white shadow-md">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="text-2xl font-bold hover:text-gray-200 transition">
          PrepChef
        </Link>

        <nav className="flex items-center gap-4">
          {user ? (
            <>
              <Link
                href="/profile"
                className="text-white hover:text-gray-200 transition"
              >
                Profile
              </Link>
              <span className="text-gray-400 text-sm">{user.email}</span>
            </>
          ) : (
            <>
              <Link
                href="/auth/login"
                className="text-white hover:text-gray-200 transition"
              >
                Log In
              </Link>
              <Link
                href="/auth/signup"
                className="bg-white text-gray-900 px-4 py-2 rounded-md font-semibold hover:bg-gray-100 transition"
              >
                Sign Up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
