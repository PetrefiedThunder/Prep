import { redirect } from 'next/navigation'
import { checkOnboardingStatus } from '@/lib/actions/stripe'

// Force dynamic rendering - this page needs runtime access to Stripe
export const dynamic = 'force-dynamic'

export default async function StripeReturnPage() {
  const result = await checkOnboardingStatus()

  if (result.onboardingComplete) {
    redirect('/owner/kitchens')
  } else {
    redirect('/owner/stripe/onboard')
  }
}
