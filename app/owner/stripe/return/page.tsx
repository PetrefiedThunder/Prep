import { redirect } from 'next/navigation'
import { checkOnboardingStatus } from '@/lib/actions/stripe'

export default async function StripeReturnPage() {
  const result = await checkOnboardingStatus()

  if (result.onboardingComplete) {
    redirect('/owner/kitchens')
  } else {
    redirect('/owner/stripe/onboard')
  }
}
