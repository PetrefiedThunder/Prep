"use client";

import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Listing } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { calculateNights, formatDateRange } from "@/lib/dates";
import { formatCurrency } from "@/lib/currency";
import { Badge } from "@/components/ui/badge";
import { track } from "@/lib/analytics";

const detailsSchema = z.object({
  firstName: z.string().min(1, "Required"),
  lastName: z.string().min(1, "Required"),
  email: z.string().email(),
  phone: z.string().min(10, "Enter a valid phone number")
});

type DetailsForm = z.infer<typeof detailsSchema>;

const paymentSchema = z.object({
  cardNumber: z.string().min(12),
  expiry: z.string().min(4),
  cvc: z.string().min(3)
});

type PaymentForm = z.infer<typeof paymentSchema>;

const steps = ["review", "details", "payment", "confirmation"] as const;

export function CheckoutFlow({ listing, startDate, endDate, guests }: { listing: Listing; startDate: string; endDate: string; guests: number }) {
  const [currentStep, setCurrentStep] = useState<typeof steps[number]>("review");
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const nights = calculateNights(startDate, endDate);
  const subtotal = nights * listing.nightlyPrice;
  const serviceFee = Math.round(subtotal * 0.12);
  const taxes = Math.round(subtotal * 0.08);
  const total = subtotal + serviceFee + taxes;

  const detailsForm = useForm<DetailsForm>({ resolver: zodResolver(detailsSchema) });
  const paymentForm = useForm<PaymentForm>({ resolver: zodResolver(paymentSchema) });

  const nextStep = async () => {
    if (currentStep === "details") {
      const valid = await detailsForm.trigger();
      if (!valid) return;
    }
    if (currentStep === "payment") {
      const valid = await paymentForm.trigger();
      if (!valid) return;
      const code = `HH-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
      setConfirmation(code);
      track({ type: "start_checkout", listingId: listing.id, total });
    }
    const index = steps.indexOf(currentStep);
    setCurrentStep(steps[Math.min(index + 1, steps.length - 1)]);
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-8">
        <Stepper currentStep={currentStep} />
        {currentStep === "review" && (
          <section className="rounded-3xl border border-border bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Review your stay</h2>
            <p className="mt-2 text-sm text-muted-ink">
              {formatDateRange(startDate, endDate)} · {guests} guests
            </p>
            <p className="mt-4 text-sm text-muted-ink">You're booking {listing.title} hosted by {listing.host.name}.</p>
            <Button className="mt-6" onClick={() => setCurrentStep("details")}>Continue</Button>
          </section>
        )}
        {currentStep === "details" && (
          <form className="rounded-3xl border border-border bg-white p-6 shadow-sm" onSubmit={(event) => { event.preventDefault(); nextStep(); }}>
            <h2 className="text-xl font-semibold">Guest details</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-ink">First name</label>
                <Input {...detailsForm.register("firstName")} />
                {detailsForm.formState.errors.firstName && <p className="text-xs text-red-600">{detailsForm.formState.errors.firstName.message}</p>}
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-ink">Last name</label>
                <Input {...detailsForm.register("lastName")} />
                {detailsForm.formState.errors.lastName && <p className="text-xs text-red-600">{detailsForm.formState.errors.lastName.message}</p>}
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-ink">Email</label>
                <Input type="email" {...detailsForm.register("email")} />
                {detailsForm.formState.errors.email && <p className="text-xs text-red-600">{detailsForm.formState.errors.email.message}</p>}
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-ink">Phone</label>
                <Input type="tel" {...detailsForm.register("phone")} />
                {detailsForm.formState.errors.phone && <p className="text-xs text-red-600">{detailsForm.formState.errors.phone.message}</p>}
              </div>
            </div>
            <Button type="submit" className="mt-6">
              Continue to payment
            </Button>
          </form>
        )}
        {currentStep === "payment" && (
          <form className="rounded-3xl border border-border bg-white p-6 shadow-sm" onSubmit={(event) => { event.preventDefault(); nextStep(); }}>
            <h2 className="text-xl font-semibold">Payment</h2>
            <div className="mt-4 grid gap-4">
              <div>
                <label className="text-xs font-semibold text-muted-ink">Card number</label>
                <Input placeholder="1234 5678 9012 3456" {...paymentForm.register("cardNumber")} />
                {paymentForm.formState.errors.cardNumber && <p className="text-xs text-red-600">Enter a valid card number</p>}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold text-muted-ink">Expiry</label>
                  <Input placeholder="MM/YY" {...paymentForm.register("expiry")} />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-ink">CVC</label>
                  <Input placeholder="123" {...paymentForm.register("cvc")} />
                </div>
              </div>
            </div>
            <Button type="submit" className="mt-6">
              Confirm booking
            </Button>
          </form>
        )}
        {currentStep === "confirmation" && (
          <section className="rounded-3xl border border-border bg-white p-6 text-center shadow-sm">
            <Badge variant="brand" className="mx-auto w-fit">Booked!</Badge>
            <h2 className="mt-4 text-2xl font-semibold">Your HarborHome is confirmed</h2>
            <p className="mt-2 text-sm text-muted-ink">
              Confirmation code: <span className="font-mono">{confirmation}</span>
            </p>
            <Button className="mt-6" onClick={() => window.location.href = "/trips"}>
              View trips
            </Button>
          </section>
        )}
      </div>
      <aside className="space-y-4 rounded-3xl border border-border bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold">Price breakdown</h3>
        <div className="space-y-2 text-sm text-muted-ink">
          <div className="flex justify-between">
            <span>{formatCurrency(listing.nightlyPrice)} × {nights} nights</span>
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
      </aside>
    </div>
  );
}

function Stepper({ currentStep }: { currentStep: typeof steps[number] }) {
  return (
    <ol className="flex flex-wrap gap-3 text-sm">
      {steps.map((step) => (
        <li key={step} className="flex items-center gap-2">
          <span
            className={`flex h-8 w-8 items-center justify-center rounded-full border ${
              steps.indexOf(step) <= steps.indexOf(currentStep) ? "border-brand bg-brand text-white" : "border-border bg-white text-muted-ink"
            }`}
          >
            {steps.indexOf(step) + 1}
          </span>
          <span className="capitalize text-muted-ink">{step}</span>
        </li>
      ))}
    </ol>
  );
}
