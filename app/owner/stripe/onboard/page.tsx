'use client'

import { useState, useEffect } from 'react'
import { createConnectAccount, createAccountLink, checkOnboardingStatus } from '@/lib/actions/stripe'
import { useRouter } from 'next/navigation'

export default function StripeOnboardPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<'checking' | 'needs_onboarding' | 'complete'>('checking')

  useEffect(() => {
    checkStatus()
  }, [])

  const checkStatus = async () => {
    const result = await checkOnboardingStatus()

    if (result.error) {
      setError(result.error)
      setLoading(false)
      return
    }

    if (result.onboardingComplete) {
      setStatus('complete')
      setLoading(false)
    } else {
      setStatus('needs_onboarding')
      setLoading(false)
    }
  }

  const handleStartOnboarding = async () => {
    setLoading(true)
    setError(null)

    // Create account if needed
    const accountResult = await createConnectAccount()
    if (accountResult.error) {
      setError(accountResult.error)
      setLoading(false)
      return
    }

    // Create account link
    const linkResult = await createAccountLink()
    if (linkResult.error) {
      setError(linkResult.error)
      setLoading(false)
      return
    }

    if (linkResult.url) {
      window.location.href = linkResult.url
    }
  }

  if (loading && status === 'checking') {
    return (
      <div className="max-w-2xl mx-auto text-center">
        <p className="text-gray-600">Checking Stripe account status...</p>
      </div>
    )
  }

  if (status === 'complete') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white p-8 rounded-lg shadow-md text-center">
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

          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Stripe Account Active
          </h1>
          <p className="text-gray-600 mb-6">
            Your Stripe account is set up and ready to receive payouts.
          </p>

          <button
            onClick={() => router.push('/owner/kitchens')}
            className="bg-gray-900 text-white px-6 py-3 rounded-lg font-semibold hover:bg-gray-800 transition"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          Set Up Payments
        </h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        <div className="mb-6">
          <p className="text-gray-700 mb-4">
            To receive payouts from bookings, you need to connect a Stripe account.
            This process is secure and takes just a few minutes.
          </p>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-semibold text-gray-900 mb-2">What you&apos;ll need:</h3>
            <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
              <li>Business or personal tax information</li>
              <li>Bank account details for payouts</li>
              <li>Government-issued ID</li>
            </ul>
          </div>
        </div>

        <button
          onClick={handleStartOnboarding}
          disabled={loading}
          className="w-full bg-gray-900 text-white py-3 rounded-lg font-semibold hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Connecting to Stripe...' : 'Connect Stripe Account'}
        </button>
      </div>
    </div>
  )
}
