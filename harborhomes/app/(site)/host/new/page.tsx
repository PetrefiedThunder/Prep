"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const steps = ["Basics", "Location", "Photos", "Pricing", "Availability"] as const;

type WizardData = {
  title: string;
  description: string;
  nightlyPrice: number;
  city: string;
  country: string;
};

export default function HostOnboarding() {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<WizardData>({
    title: "",
    description: "",
    nightlyPrice: 250,
    city: "",
    country: ""
  });

  const next = () => setStep((prev) => Math.min(prev + 1, steps.length - 1));
  const back = () => setStep((prev) => Math.max(prev - 1, 0));

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-10 space-y-2 text-center">
        <p className="text-sm uppercase tracking-wide text-brand">Host onboarding</p>
        <h1 className="text-3xl font-semibold">Share your HarborHome</h1>
        <p className="text-muted-ink">Guided setup with map preview, amenities, and pricing.</p>
      </header>
      <div className="mb-6 flex justify-center gap-2">
        {steps.map((label, index) => (
          <span
            key={label}
            className={`h-2 flex-1 rounded-full ${index <= step ? "bg-brand" : "bg-border"}`}
            aria-hidden
          />
        ))}
      </div>
      <div className="space-y-6 rounded-3xl border border-border bg-white p-6 shadow-sm">
        {step === 0 && (
          <div className="space-y-4">
            <label className="block text-sm font-semibold text-muted-ink">
              Listing name
              <Input
                className="mt-2"
                value={data.title}
                onChange={(event) => setData((prev) => ({ ...prev, title: event.target.value }))}
                placeholder="e.g. Harbor-view loft"
              />
            </label>
            <label className="block text-sm font-semibold text-muted-ink">
              Description
              <textarea
                className="mt-2 h-32 w-full rounded-2xl border border-border px-4 py-3 text-sm"
                value={data.description}
                onChange={(event) => setData((prev) => ({ ...prev, description: event.target.value }))}
              />
            </label>
          </div>
        )}
        {step === 1 && (
          <div className="space-y-4">
            <label className="block text-sm font-semibold text-muted-ink">
              City
              <Input
                className="mt-2"
                value={data.city}
                onChange={(event) => setData((prev) => ({ ...prev, city: event.target.value }))}
              />
            </label>
            <label className="block text-sm font-semibold text-muted-ink">
              Country
              <Input
                className="mt-2"
                value={data.country}
                onChange={(event) => setData((prev) => ({ ...prev, country: event.target.value }))}
              />
            </label>
            <div className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-ink">
              Map drop coming soon. Drag and drop your pin.
            </div>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-ink">
              Upload photos (drag and drop or browse)
            </div>
          </div>
        )}
        {step === 3 && (
          <div className="space-y-4">
            <label className="block text-sm font-semibold text-muted-ink">
              Nightly rate
              <Input
                type="number"
                className="mt-2"
                value={data.nightlyPrice}
                onChange={(event) => setData((prev) => ({ ...prev, nightlyPrice: Number(event.target.value) }))}
              />
            </label>
            <div className="rounded-2xl bg-surface p-4 text-sm text-muted-ink">
              We analyze comparable HarborHomes and local demand to recommend competitive pricing.
            </div>
          </div>
        )}
        {step === 4 && (
          <div className="space-y-4 text-sm text-muted-ink">
            <p>Set available months, blackout dates, and instant booking preferences.</p>
            <div className="rounded-2xl border border-dashed border-border p-10 text-center">
              Calendar editor coming soon.
            </div>
          </div>
        )}
        <div className="flex justify-between">
          <Button variant="ghost" disabled={step === 0} onClick={back}>
            Back
          </Button>
          {step < steps.length - 1 ? (
            <Button onClick={next}>Continue</Button>
          ) : (
            <Button onClick={() => alert("Listing submitted!")}>Finish</Button>
          )}
        </div>
      </div>
    </div>
  );
}
