'use client';

import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Users } from 'lucide-react';
import { format } from 'date-fns';
import { Button, Popover, PopoverContent, PopoverTrigger } from '@/components/ui';
import { Calendar } from '@/components/ui/calendar';
import { formatCurrency } from '@/lib/currency';
import { nightsBetween } from '@/lib/dates';
import { trackEvent } from '@/lib/analytics';

export interface BookingCardProps {
  listingId: string;
  pricePerNight: number;
}

export const BookingCard = ({ listingId, pricePerNight }: BookingCardProps) => {
  const [dates, setDates] = useState<{ from?: Date; to?: Date }>({});
  const [guests, setGuests] = useState(1);
  const router = useRouter();
  const pathname = usePathname();
  const localeSegment = pathname.split('/')[1] || 'en';

  const nights = dates.from && dates.to ? nightsBetween(dates.from.toISOString(), dates.to.toISOString()) : 1;
  const subtotal = pricePerNight * nights;
  const serviceFee = Math.round(subtotal * 0.1);
  const total = subtotal + serviceFee;

  return (
    <aside className="sticky top-28 rounded-3xl border border-border bg-white p-6 shadow-xl">
      <div className="flex items-baseline justify-between">
        <span className="text-2xl font-semibold text-ink">{formatCurrency(pricePerNight)}</span>
        <span className="text-sm text-muted-ink">night</span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-sm font-semibold text-ink">
        <Popover>
          <PopoverTrigger asChild>
            <button className="focus-ring flex flex-col rounded-2xl border border-border px-4 py-3">
              <span className="text-xs uppercase text-muted-ink">Check-in</span>
              <span>{dates.from ? format(dates.from, 'MMM d') : 'Select'}</span>
            </button>
          </PopoverTrigger>
          <PopoverContent className="p-0">
            <Calendar
              mode="range"
              numberOfMonths={2}
              selected={dates.from && dates.to ? { from: dates.from, to: dates.to } : undefined}
              onSelect={(range) => setDates(range ?? {})}
              disabled={{ before: new Date() }}
            />
          </PopoverContent>
        </Popover>
        <Popover>
          <PopoverTrigger asChild>
            <button className="focus-ring flex flex-col rounded-2xl border border-border px-4 py-3">
              <span className="text-xs uppercase text-muted-ink">Check-out</span>
              <span>{dates.to ? format(dates.to, 'MMM d') : 'Select'}</span>
            </button>
          </PopoverTrigger>
          <PopoverContent className="p-0">
            <Calendar
              mode="range"
              numberOfMonths={2}
              selected={dates.from && dates.to ? { from: dates.from, to: dates.to } : undefined}
              onSelect={(range) => setDates(range ?? {})}
              disabled={{ before: new Date() }}
            />
          </PopoverContent>
        </Popover>
        <div className="col-span-2">
          <Popover>
            <PopoverTrigger asChild>
              <button className="focus-ring flex w-full items-center justify-between rounded-2xl border border-border px-4 py-3">
                <div className="flex flex-col text-left">
                  <span className="text-xs uppercase text-muted-ink">Guests</span>
                  <span>{guests} {guests === 1 ? 'guest' : 'guests'}</span>
                </div>
                <Users className="h-5 w-5" />
              </button>
            </PopoverTrigger>
            <PopoverContent>
              <div className="flex items-center justify-between gap-4">
                <button className="h-10 w-10 rounded-full border border-border" onClick={() => setGuests(Math.max(1, guests - 1))}>
                  -
                </button>
                <span className="text-lg font-semibold">{guests}</span>
                <button className="h-10 w-10 rounded-full border border-border" onClick={() => setGuests(guests + 1)}>
                  +
                </button>
              </div>
            </PopoverContent>
          </Popover>
        </div>
      </div>
      <div className="mt-6 space-y-2 text-sm text-muted-ink">
        <div className="flex justify-between">
          <span>
            {formatCurrency(pricePerNight)} × {nights} nights
          </span>
          <span>{formatCurrency(subtotal)}</span>
        </div>
        <div className="flex justify-between">
          <span>Service fee</span>
          <span>{formatCurrency(serviceFee)}</span>
        </div>
        <hr />
        <div className="flex justify-between text-base font-semibold text-ink">
          <span>Total</span>
          <span>{formatCurrency(total)}</span>
        </div>
      </div>
      <Button
        className="mt-6 w-full"
        onClick={() => {
          const params = new URLSearchParams();
          if (dates.from) params.set('checkin', dates.from.toISOString());
          if (dates.to) params.set('checkout', dates.to.toISOString());
          params.set('guests', String(guests));
          trackEvent({ name: 'start_checkout', properties: { listingId, guests } });
          router.push(`/${localeSegment}/checkout/${listingId}?${params.toString()}`);
        }}
      >
        Continue
      </Button>
    </aside>
  );
};
