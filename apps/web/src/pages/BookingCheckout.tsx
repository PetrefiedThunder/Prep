import { useEffect, useMemo, useState } from 'react';

type BusinessReadiness = {
  business_id: string;
  readiness_score: number;
  readiness_stage: string;
  gating_requirements: string[];
  outstanding_actions: string[];
};

type CheckoutLineItem = {
  name: string;
  amount: number;
  quantity: number;
  taxable: boolean;
  refundable: boolean;
};

type CheckoutPaymentResponse = {
  id: string;
  status: string;
  currency: string;
  total_amount: number;
  line_items: CheckoutLineItem[];
  payment_provider: string;
  provider_reference: string | null;
  receipt_url: string | null;
  refund_reason: string | null;
  refund_requested_at: string | null;
  refunded_at: string | null;
  created_at: string;
  updated_at: string;
};

const readinessThreshold = 0.6;

const baseLineItems: CheckoutLineItem[] = [
  { name: 'Kitchen rental (4 hours)', amount: 48000, quantity: 1, taxable: false, refundable: false },
  { name: 'Prep platform fee', amount: 5500, quantity: 1, taxable: false, refundable: true },
];

const optionalLineItems: CheckoutLineItem[] = [
  { name: 'Walk-through consultation', amount: 2500, quantity: 1, taxable: false, refundable: true },
  { name: 'Equipment sterilization add-on', amount: 1800, quantity: 1, taxable: false, refundable: false },
];

const locales = [
  { value: 'en-US', label: 'English (US)' },
  { value: 'es-MX', label: 'Español (México)' },
  { value: 'fr-CA', label: 'Français (Canada)' },
];

function currencyFormatter(locale: string, currency: string) {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  });
}

export default function BookingCheckout() {
  const [businessId, setBusinessId] = useState('');
  const [bookingId, setBookingId] = useState('');
  const [locale, setLocale] = useState(locales[0]?.value ?? 'en-US');
  const [selectedExtras, setSelectedExtras] = useState<string[]>([]);
  const [readiness, setReadiness] = useState<BusinessReadiness | null>(null);
  const [payment, setPayment] = useState<CheckoutPaymentResponse | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refundStatus, setRefundStatus] = useState<string | null>(null);

  const formatter = useMemo(() => currencyFormatter(locale, 'USD'), [locale]);

  const lineItems = useMemo(() => {
    const extras = optionalLineItems.filter((item) => selectedExtras.includes(item.name));
    return [...baseLineItems, ...extras];
  }, [selectedExtras]);

  const totalMinorUnits = useMemo(
    () => lineItems.reduce((sum, item) => sum + item.amount * item.quantity, 0),
    [lineItems]
  );

  const localizedTotal = formatter.format(totalMinorUnits / 100);

  useEffect(() => {
    if (!businessId) {
      setReadiness(null);
      return;
    }

    let cancelled = false;
    const loadReadiness = async () => {
      try {
        const response = await fetch(`/api/v1/platform/business/${businessId}/readiness`);
        if (!response.ok) {
          throw new Error(`Readiness request failed: ${response.status}`);
        }
        const data: BusinessReadiness = await response.json();
        if (!cancelled) {
          setReadiness(data);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setReadiness(null);
        }
      }
    };

    void loadReadiness();
    return () => {
      cancelled = true;
    };
  }, [businessId]);

  const readinessGateActive =
    readiness != null && readiness.readiness_score < readinessThreshold && readiness.gating_requirements.length > 0;

  const confirmBooking = async () => {
    setLoading(true);
    setStatus(null);
    setError(null);
    setRefundStatus(null);
    try {
      const payload = {
        currency: 'usd',
        line_items: lineItems,
        business_id: businessId || undefined,
        booking_id: bookingId || undefined,
        requirements_gate: true,
        minimum_readiness_score: readinessThreshold,
        metadata: {
          source: 'booking_checkout_ui',
          locale,
        },
      };
      const response = await fetch('/api/v1/platform/payments/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Checkout failed: ${response.status}`);
      }
      const paymentResponse: CheckoutPaymentResponse = await response.json();
      setPayment(paymentResponse);
      setStatus('Booked!');
    } catch (err) {
      console.error(err);
      setError('Unable to finalize checkout. Confirm your readiness tasks and try again.');
      setStatus('Failed');
    } finally {
      setLoading(false);
    }
  };

  const initiateRefund = async () => {
    if (!payment) return;
    setRefundStatus('Submitting refund request…');
    try {
      const response = await fetch('/api/v1/platform/payments/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'refund',
          existing_payment_id: payment.id,
          refund_reason: 'Guest requested cancellation',
        }),
      });
      if (!response.ok) {
        throw new Error(`Refund failed: ${response.status}`);
      }
      const refundResponse: CheckoutPaymentResponse = await response.json();
      setPayment(refundResponse);
      setRefundStatus('Refund in progress');
    } catch (err) {
      console.error(err);
      setRefundStatus('Refund failed — reach out to support.');
    }
  };

  const toggleExtra = (name: string) => {
    setSelectedExtras((current) =>
      current.includes(name) ? current.filter((value) => value !== name) : [...current, name]
    );
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Checkout</h1>
        <p className="text-sm text-slate-600">
          Review line items, confirm readiness, and capture payments with localized receipts.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <label className="flex flex-col text-sm font-medium text-slate-700">
          Business ID
          <input
            value={businessId}
            onChange={(event) => setBusinessId(event.target.value.trim())}
            placeholder="UUID for the business profile"
            className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
          />
        </label>
        <label className="flex flex-col text-sm font-medium text-slate-700">
          Booking ID
          <input
            value={bookingId}
            onChange={(event) => setBookingId(event.target.value.trim())}
            placeholder="Optional — associate with a booking"
            className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
          />
        </label>
        <label className="flex flex-col text-sm font-medium text-slate-700">
          Locale
          <select
            value={locale}
            onChange={(event) => setLocale(event.target.value)}
            className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
          >
            {locales.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Line item</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3 text-right">Quantity</th>
              <th className="px-4 py-3 text-right">Total</th>
              <th className="px-4 py-3 text-center">Refundable</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {lineItems.map((item) => (
              <tr key={item.name}>
                <td className="px-4 py-3">{item.name}</td>
                <td className="px-4 py-3 text-right">{formatter.format(item.amount / 100)}</td>
                <td className="px-4 py-3 text-right">{item.quantity}</td>
                <td className="px-4 py-3 text-right">{formatter.format((item.amount * item.quantity) / 100)}</td>
                <td className="px-4 py-3 text-center">{item.refundable ? '✔️' : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex items-center justify-between bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
          <span>Localized total ({locale})</span>
          <span>{localizedTotal}</span>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Optional services</h2>
        <p className="mt-1 text-xs text-slate-500">Toggle concierge extras to update the quote automatically.</p>
        <ul className="mt-3 grid gap-3 md:grid-cols-2">
          {optionalLineItems.map((item) => {
            const checked = selectedExtras.includes(item.name);
            return (
              <li key={item.name} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2">
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleExtra(item.name)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>{item.name}</span>
                </label>
                <span className="text-sm font-medium">{formatter.format(item.amount / 100)}</span>
              </li>
            );
          })}
        </ul>
      </section>

      {readinessGateActive && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Complete the following requirements before checkout: {readiness?.gating_requirements.join(', ')}.
        </div>
      )}

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={confirmBooking}
          disabled={loading || readinessGateActive}
          className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {loading ? 'Processing…' : 'Confirm booking'}
        </button>
        <button
          type="button"
          onClick={initiateRefund}
          disabled={!payment}
          className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
        >
          Initiate refund
        </button>
      </div>

      {status && <p className="text-sm text-slate-700">Status: {status}</p>}
      {refundStatus && <p className="text-sm text-slate-700">{refundStatus}</p>}

      {payment && (
        <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          <p className="font-semibold">Payment captured via {payment.payment_provider}</p>
          <p className="mt-1">Reference: {payment.provider_reference ?? payment.id}</p>
          <p className="mt-1">Amount: {formatter.format(payment.total_amount)}</p>
          {payment.receipt_url && (
            <a
              href={payment.receipt_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex text-indigo-700 underline"
            >
              View receipt
            </a>
          )}
          {payment.refund_requested_at && (
            <p className="mt-1">Refund requested {new Date(payment.refund_requested_at).toLocaleString(locale)}</p>
          )}
        </section>
      )}
    </div>
  );
}
