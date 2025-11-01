import { useMemo, useState } from 'react';

import type { BusinessReadinessResponse, CheckoutLineItem, CheckoutPaymentResponse } from './types';

const currencyFormatter = (locale: string, currency: string) =>
  new Intl.NumberFormat(locale, { style: 'currency', currency, minimumFractionDigits: 2 });

type FeeEstimatorStepProps = {
  businessId: string;
  readiness: BusinessReadinessResponse | null;
  locale?: string;
  onBack: () => void;
  onContinue: (estimate: CheckoutPaymentResponse | null) => void;
};

const baseItems: CheckoutLineItem[] = [
  { name: 'Local health department review', amount: 12000, quantity: 1, taxable: false, refundable: false },
  { name: 'Prep onboarding fee', amount: 4500, quantity: 1, taxable: false, refundable: true },
];

const optionalItems: CheckoutLineItem[] = [
  { name: 'Rush document processing', amount: 8500, quantity: 1, taxable: false, refundable: true },
  { name: 'Food handler certification bundle', amount: 6000, quantity: 1, taxable: false, refundable: true },
];

export default function FeeEstimatorStep({
  businessId,
  readiness,
  locale = 'en-US',
  onBack,
  onContinue,
}: FeeEstimatorStepProps) {
  const [selectedExtras, setSelectedExtras] = useState<string[]>([]);
  const [estimate, setEstimate] = useState<CheckoutPaymentResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allItems = useMemo(() => {
    const extras = optionalItems.filter((item) => selectedExtras.includes(item.name));
    return [...baseItems, ...extras];
  }, [selectedExtras]);

  const totalInMinorUnits = useMemo(
    () => allItems.reduce((sum, item) => sum + item.amount * item.quantity, 0),
    [allItems]
  );

  const formatter = useMemo(() => currencyFormatter(locale, 'USD'), [locale]);

  const toggleExtra = (name: string) => {
    setSelectedExtras((current) =>
      current.includes(name) ? current.filter((value) => value !== name) : [...current, name]
    );
  };

  const generateEstimate = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        currency: 'usd',
        line_items: allItems,
        business_id: readiness?.business_id ?? businessId,
        requirements_gate: false,
        metadata: {
          source: 'onboarding_fee_estimator',
          estimate_only: true,
        },
      };
      const response = await fetch('/api/v1/platform/payments/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Failed to create checkout estimate: ${response.status}`);
      }
      const data: CheckoutPaymentResponse = await response.json();
      setEstimate(data);
      onContinue(data);
    } catch (err) {
      console.error(err);
      setError('Unable to create an estimate right now. Please review the line items and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const localizedTotal = formatter.format(totalInMinorUnits / 100);
  const readinessGateActive = readiness?.readiness_stage === 'not_ready';

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-xl font-semibold">Step 2: Estimate onboarding fees</h2>
        <p className="text-sm text-slate-600">
          Tailor your onboarding package. We surface mandatory line items automatically and let you add concierge services.
        </p>
      </header>

      {readinessGateActive && (
        <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Heads up! You still have outstanding requirements. We will hold the checkout session until those are complete.
        </p>
      )}

      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold">Included services</h3>
        <ul className="space-y-2">
          {baseItems.map((item) => (
            <li key={item.name} className="flex items-center justify-between text-sm">
              <span>{item.name}</span>
              <span className="font-medium">{formatter.format((item.amount * item.quantity) / 100)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold">Optional add-ons</h3>
        <ul className="space-y-3">
          {optionalItems.map((item) => {
            const checked = selectedExtras.includes(item.name);
            return (
              <li key={item.name} className="flex items-center justify-between">
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleExtra(item.name)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>{item.name}</span>
                </label>
                <span className="text-sm font-medium">
                  {formatter.format((item.amount * item.quantity) / 100)}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-600">Estimated total</span>
          <span className="text-xl font-bold text-slate-900">{localizedTotal}</span>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Taxes are not collected on regulatory fees. Refundable line items can be returned if your launch timeline changes.
        </p>
      </section>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm"
        >
          Back to requirements
        </button>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={generateEstimate}
            disabled={submitting}
            className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {submitting ? 'Generating…' : 'Generate fee quote'}
          </button>
          <button
            type="button"
            onClick={() => onContinue(estimate)}
            disabled={!estimate}
            className="inline-flex items-center rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Continue to document upload
          </button>
        </div>
      </div>

      {estimate && (
        <aside className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          Checkout session {estimate.provider_reference ?? estimate.id} is ready. We will only capture payment once you submit
          the required documents.
        </aside>
      )}
    </div>
  );
}
