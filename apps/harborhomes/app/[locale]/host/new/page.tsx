'use client';

import { useState } from 'react';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@/components/ui';

const steps = ['Basics', 'Location', 'Photos', 'Pricing', 'Availability'] as const;

type Step = (typeof steps)[number];

export default function HostOnboarding() {
  const [stepIndex, setStepIndex] = useState(0);
  const step = steps[stepIndex];

  return (
    <Card>
      <CardHeader>
        <CardTitle>List your HarborHome</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <ol className="flex gap-3 text-xs uppercase text-muted-ink">
          {steps.map((value, index) => (
            <li key={value} className={`flex items-center gap-2 ${index === stepIndex ? 'text-brand' : ''}`}>
              <span className={`inline-flex h-6 w-6 items-center justify-center rounded-full border ${index === stepIndex ? 'border-brand bg-brand text-brand-contrast' : 'border-border'}`}>
                {index + 1}
              </span>
              {value}
            </li>
          ))}
        </ol>

        {step === 'Basics' && (
          <div className="grid gap-4">
            <div>
              <Label htmlFor="title">Title</Label>
              <Input id="title" placeholder="Describe your stay" />
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <textarea id="description" className="h-24 w-full rounded-2xl border border-border p-3 text-sm" />
            </div>
          </div>
        )}
        {step === 'Location' && (
          <div className="grid gap-4">
            <Label htmlFor="address">Address</Label>
            <Input id="address" placeholder="123 Harbor Way" />
            <div className="h-56 rounded-3xl border border-border bg-surface" aria-label="Map placeholder" />
          </div>
        )}
        {step === 'Photos' && <div className="h-40 rounded-3xl border border-dashed border-border" aria-label="Upload area" />}
        {step === 'Pricing' && (
          <div className="grid gap-4">
            <Label htmlFor="price">Nightly rate</Label>
            <Input id="price" type="number" min={50} step={10} defaultValue={200} />
          </div>
        )}
        {step === 'Availability' && (
          <div className="grid gap-4">
            <p className="text-sm text-muted-ink">Set blocked dates and instant book rules.</p>
            <div className="h-56 rounded-3xl border border-border bg-surface" />
          </div>
        )}
        <div className="flex justify-between">
          <Button variant="secondary" disabled={stepIndex === 0} onClick={() => setStepIndex((index) => Math.max(0, index - 1))}>
            Back
          </Button>
          <Button onClick={() => setStepIndex((index) => Math.min(steps.length - 1, index + 1))}>
            {stepIndex === steps.length - 1 ? 'Finish' : 'Next'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
