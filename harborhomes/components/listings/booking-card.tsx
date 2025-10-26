"use client";

import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { LabelledCounter } from "@/components/search/selector-counter";
import { useState } from "react";
import { addDays, differenceInCalendarDays, format } from "date-fns";
import { formatCurrency } from "@/lib/currency";
import type { Listing } from "@/lib/types";
import { track } from "@/lib/analytics";

const schema = z.object({
  guests: z.number().min(1).max(10),
  startDate: z.date(),
  endDate: z.date()
});

type FormValues = z.infer<typeof schema>;

export function BookingCard({ listing }: { listing: Listing }) {
  const [open, setOpen] = useState(false);
  const {
    handleSubmit,
    setValue,
    watch,
    formState: { errors }
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      guests: 2,
      startDate: addDays(new Date(), 7),
      endDate: addDays(new Date(), 10)
    }
  });

  const onSubmit = (values: FormValues) => {
    const nights = differenceInCalendarDays(values.endDate, values.startDate) || 1;
    const total = nights * listing.nightlyPrice + 120;
    track({ type: "start_checkout", listingId: listing.id, total });
    window.location.href = `/checkout/${listing.id}?start=${values.startDate.toISOString()}&end=${values.endDate.toISOString()}&guests=${values.guests}`;
  };

  const values = watch();
  const nights = differenceInCalendarDays(values.endDate, values.startDate) || 1;
  const subtotal = nights * listing.nightlyPrice;
  const serviceFee = Math.round(subtotal * 0.12);
  const taxes = Math.round(subtotal * 0.08);
  const total = subtotal + serviceFee + taxes;

  return (
    <aside className="sticky top-28 space-y-6 rounded-3xl border border-border bg-white p-6 shadow-floating">
      <div>
        <p className="text-2xl font-semibold text-ink">{formatCurrency(listing.nightlyPrice)}</p>
        <p className="text-sm text-muted-ink">per night</p>
      </div>
      <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
        <div className="grid gap-3">
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <button
                type="button"
                className="w-full rounded-2xl border border-border px-4 py-3 text-left text-sm"
                aria-label="Select dates"
              >
                <p className="font-semibold text-ink">Dates</p>
                <p className="text-muted-ink">
                  {format(values.startDate, "MMM d")} – {format(values.endDate, "MMM d")}
                </p>
              </button>
            </PopoverTrigger>
            <PopoverContent align="center" className="w-auto">
              <Calendar
                mode="range"
                selected={{ from: values.startDate, to: values.endDate }}
                onSelect={(range) => {
                  if (range?.from) setValue("startDate", range.from, { shouldValidate: true });
                  if (range?.to) setValue("endDate", range.to, { shouldValidate: true });
                }}
                numberOfMonths={2}
                disabled={(date) => date < new Date()}
              />
            </PopoverContent>
          </Popover>
          <LabelledCounter
            label="Guests"
            helper="Max 10"
            value={values.guests}
            onChange={(value) => setValue("guests", value, { shouldValidate: true })}
          />
          {errors.guests && <p className="text-xs text-red-600">{errors.guests.message}</p>}
        </div>
        <div className="space-y-2 text-sm text-muted-ink">
          <div className="flex justify-between">
            <span>
              {formatCurrency(listing.nightlyPrice)} × {nights} nights
            </span>
            <span>{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span>Service fee</span>
            <span>{formatCurrency(serviceFee)}</span>
          </div>
          <div className="flex justify-between">
            <span>Taxes</span>
            <span>{formatCurrency(taxes)}</span>
          </div>
          <div className="flex justify-between border-t border-border pt-2 text-ink">
            <span>Total</span>
            <span className="font-semibold">{formatCurrency(total)}</span>
          </div>
        </div>
        <Button type="submit" size="lg" className="w-full rounded-full">
          Request to book
        </Button>
      </form>
    </aside>
  );
}
