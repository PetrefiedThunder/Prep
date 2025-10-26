'use client';

import { useMemo, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { listings } from '@/lib/mock-data';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@/components/ui';
import { formatCurrency } from '@/lib/currency';

const schema = z.object({
  fullName: z.string().min(2),
  email: z.string().email(),
  phone: z.string().min(7)
});

type FormValues = z.infer<typeof schema>;

export default function CheckoutPage({ params: { id } }: { params: { id: string } }) {
  const listing = listings.find((item) => item.id === id);
  const router = useRouter();
  const search = useSearchParams();
  const pathname = usePathname();
  const locale = pathname.split('/')[1] || 'en';
  const [step, setStep] = useState<'review' | 'details' | 'payment' | 'confirmation'>('review');
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { fullName: '', email: '', phone: '' } });

  const summary = useMemo(() => {
    if (!listing) return null;
    const nights = search.get('checkin') && search.get('checkout') ? 3 : 1;
    const subtotal = listing.pricePerNight * nights;
    const serviceFee = Math.round(subtotal * 0.1);
    return { nights, subtotal, serviceFee, total: subtotal + serviceFee };
  }, [listing, search]);

  if (!listing) {
    return <p>Listing not found.</p>;
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-semibold text-ink">Checkout</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <ol className="grid gap-4 text-sm">
            {['review', 'details', 'payment', 'confirmation'].map((value) => (
              <li key={value} className={`flex items-center gap-3 ${step === value ? 'text-brand' : 'text-muted-ink'}`}>
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full border ${
                    step === value ? 'border-brand bg-brand text-brand-contrast' : 'border-border'
                  }`}
                >
                  {value === 'review' ? 1 : value === 'details' ? 2 : value === 'payment' ? 3 : 4}
                </span>
                {value.toUpperCase()}
              </li>
            ))}
          </ol>

          {step === 'review' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-ink">Review your stay</h2>
              <p className="text-sm text-muted-ink">
                {listing.title} · {listing.city}
              </p>
              <Button onClick={() => setStep('details')} className="mt-4">
                Continue to details
              </Button>
            </div>
          )}

          {step === 'details' && (
            <form
              className="space-y-4"
              onSubmit={form.handleSubmit(() => {
                setStep('payment');
              })}
            >
              <div>
                <Label htmlFor="fullName">Full name</Label>
                <Input id="fullName" {...form.register('fullName')} />
                {form.formState.errors.fullName && (
                  <p className="text-xs text-red-500">{form.formState.errors.fullName.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" {...form.register('email')} />
                {form.formState.errors.email && (
                  <p className="text-xs text-red-500">{form.formState.errors.email.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input id="phone" type="tel" {...form.register('phone')} />
                {form.formState.errors.phone && (
                  <p className="text-xs text-red-500">{form.formState.errors.phone.message}</p>
                )}
              </div>
              <Button type="submit">Save details</Button>
            </form>
          )}

          {step === 'payment' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-ink">Secure your stay</h2>
              <p className="text-sm text-muted-ink">Payments are simulated in this demo.</p>
              <Button onClick={() => setStep('confirmation')}>Complete booking</Button>
            </div>
          )}

          {step === 'confirmation' && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-ink">All set!</h2>
              <p className="text-sm text-muted-ink">
                Confirmation code HH-{Math.random().toString(36).slice(2, 8).toUpperCase()}
              </p>
              <Button onClick={() => router.push(`/${locale}/trips`)}>View trips</Button>
            </div>
          )}
        </CardContent>
      </Card>
      {summary && (
        <Card>
          <CardHeader>
            <CardTitle>Price breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-ink">
            <div className="flex justify-between">
              <span>
                {formatCurrency(listing.pricePerNight)} × {summary.nights} nights
              </span>
              <span>{formatCurrency(summary.subtotal)}</span>
            </div>
            <div className="flex justify-between">
              <span>Service fee</span>
              <span>{formatCurrency(summary.serviceFee)}</span>
            </div>
            <hr />
            <div className="flex justify-between text-base font-semibold text-ink">
              <span>Total</span>
              <span>{formatCurrency(summary.total)}</span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
