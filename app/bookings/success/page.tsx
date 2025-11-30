import Link from 'next/link'

export default function BookingSuccessPage() {
  return (
    <div className="max-w-2xl mx-auto text-center">
      <div className="bg-white p-12 rounded-lg shadow-md">
        <div className="mb-6">
          <svg
            className="mx-auto h-16 w-16 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Booking Confirmed!
        </h1>

        <p className="text-gray-600 mb-8">
          Your kitchen booking has been confirmed. You will receive a confirmation email shortly.
        </p>

        <div className="flex gap-4 justify-center">
          <Link
            href="/renter/bookings"
            className="bg-gray-900 text-white px-6 py-3 rounded-lg font-semibold hover:bg-gray-800 transition"
          >
            View My Bookings
          </Link>
          <Link
            href="/kitchens"
            className="border-2 border-gray-900 text-gray-900 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition"
          >
            Browse More Kitchens
          </Link>
        </div>
      </div>
    </div>
  )
}
