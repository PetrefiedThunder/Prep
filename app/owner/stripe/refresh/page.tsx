import { redirect } from 'next/navigation'

export default function StripeRefreshPage() {
  redirect('/owner/stripe/onboard')
}
