import { redirect } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
import { getUserBookings } from '@/lib/actions/bookings'
import type { BookingWithKitchen } from '@/lib/types'

export default async function RenterBookingsPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const result = await getUserBookings()

  if (result.error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Error loading bookings: {result.error}
        </div>
      </div>
    )
  }

  const bookings = result.data || []
  const upcoming = bookings.filter(b => new Date(b.start_time) > new Date() && b.status === 'confirmed')
  const past = bookings.filter(b => new Date(b.start_time) <= new Date() || b.status !== 'confirmed')

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">My Bookings</h1>

      {bookings.length === 0 ? (
        <div className="bg-white p-12 rounded-lg shadow-md text-center">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            No bookings yet
          </h2>
          <p className="text-gray-600 mb-6">
            Start by browsing available commercial kitchens in your area.
          </p>
          <Link
            href="/kitchens"
            className="inline-block bg-gray-900 text-white px-8 py-3 rounded-lg font-semibold hover:bg-gray-800 transition"
          >
            Browse Kitchens
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Upcoming Bookings */}
          {upcoming.length > 0 && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">
                Upcoming ({upcoming.length})
              </h2>
              <div className="space-y-4">
                {upcoming.map((booking) => (
                  <BookingCard key={booking.id} booking={booking} />
                ))}
              </div>
            </div>
          )}

          {/* Past Bookings */}
          {past.length > 0 && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">
                Past ({past.length})
              </h2>
              <div className="space-y-4">
                {past.map((booking) => (
                  <BookingCard key={booking.id} booking={booking} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function BookingCard({ booking }: { booking: BookingWithKitchen }) {
  const startDate = new Date(booking.start_time)
  const endDate = new Date(booking.end_time)

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-1">
            {booking.kitchens.title}
          </h3>
          <p className="text-sm text-gray-600">
            {booking.kitchens.address}, {booking.kitchens.city}, {booking.kitchens.state}
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">
            ${booking.total_amount}
          </div>
          <div className={`text-sm font-semibold ${
            booking.status === 'confirmed' ? 'text-green-600' :
            booking.status === 'cancelled' ? 'text-red-600' :
            'text-gray-600'
          }`}>
            {booking.status.charAt(0).toUpperCase() + booking.status.slice(1)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-600">Start</div>
          <div className="font-semibold">
            {startDate.toLocaleString()}
          </div>
        </div>
        <div>
          <div className="text-gray-600">End</div>
          <div className="font-semibold">
            {endDate.toLocaleString()}
          </div>
        </div>
        <div>
          <div className="text-gray-600">Duration</div>
          <div className="font-semibold">
            {booking.total_hours} hours
          </div>
        </div>
        <div>
          <div className="text-gray-600">Rate</div>
          <div className="font-semibold">
            ${booking.price_per_hour}/hour
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t">
        <Link
          href={`/kitchens/${booking.kitchens.id}`}
          className="text-gray-900 font-semibold hover:underline"
        >
          View Kitchen Details →
        </Link>
      </div>
    </div>
  )
}
