import { useMemo, useState } from 'react';

import { FeeEstimator, LineItem } from '../components/onboarding/FeeEstimator';
import { Requirement, RequirementsChecklist } from '../components/onboarding/RequirementsChecklist';

const COPY = {
  'en-us': {
    title: 'Checkout',
    subtitle: 'Verify requirements, review fees, then confirm your booking with automated receipts.',
    businessLabel: 'Business ID',
    bookingLabel: 'Booking ID (optional)',
    localeLabel: 'Language',
    requirementsTitle: 'Compliance readiness',
    feesTitle: 'Itemized fees',
    paymentTitle: 'Payment & receipts',
    confirmCta: 'Confirm booking and charge card',
    refundCta: 'Initiate refund',
    receiptLabel: 'Receipt',
    refundNotice: 'Refunds will settle back to the original payment method.',
    requirementsGate: 'Complete all required onboarding steps before booking.',
    readyMessage: 'All required steps completed — you are good to go! ✅',
    localeOptions: [
      { value: 'en-US', label: 'English (US)' },
      { value: 'es-ES', label: 'Español (ES)' },
    ],
  },
  'es-es': {
    title: 'Pago',
    subtitle: 'Verifica requisitos, revisa las tarifas y confirma tu reserva con recibos automáticos.',
    businessLabel: 'ID de negocio',
    bookingLabel: 'ID de reserva (opcional)',
    localeLabel: 'Idioma',
    requirementsTitle: 'Preparación de cumplimiento',
    feesTitle: 'Tarifas detalladas',
    paymentTitle: 'Pago y recibos',
    confirmCta: 'Confirmar reserva y cobrar',
    refundCta: 'Iniciar reembolso',
    receiptLabel: 'Recibo',
    refundNotice: 'Los reembolsos regresan al método de pago original.',
    requirementsGate: 'Completa todos los pasos de incorporación requeridos antes de reservar.',
    readyMessage: 'Todos los pasos requeridos completados — ¡listo para continuar! ✅',
    localeOptions: [
      { value: 'en-US', label: 'English (US)' },
      { value: 'es-ES', label: 'Español (ES)' },
    ],
  },
};

const ALLOWED_STATUSES = new Set(['approved', 'completed', 'complete']);

export default function BookingCheckout() {
  const browserLocale = typeof window !== 'undefined' ? window.navigator.language : 'en-US';
  const [locale, setLocale] = useState(browserLocale);
  const [businessId, setBusinessId] = useState('');
  const [bookingId, setBookingId] = useState('');
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [readinessScore, setReadinessScore] = useState(0);
  const [estimate, setEstimate] = useState<{ totalCents: number; lineItems: LineItem[] }>({ totalCents: 0, lineItems: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkoutResult, setCheckoutResult] = useState<{
    paymentId: string;
    status: string;
    receiptUrl?: string | null;
    clientSecret?: string | null;
    refundedAmountCents?: number | null;
  } | null>(null);

  const normalizedLocale = (locale ?? 'en-US').toLowerCase();
  const copy = COPY[normalizedLocale as keyof typeof COPY] ?? COPY['en-us'];
  const currency = normalizedLocale === 'es-es' ? 'eur' : 'usd';

  const requirementsMet = useMemo(() => {
    if (requirements.length === 0) {
      return false;
    }
    return requirements.every((requirement) => ALLOWED_STATUSES.has(requirement.status.toLowerCase())) && readinessScore >= 0.6;
  }, [requirements, readinessScore]);

  const confirmDisabled =
    loading || !businessId || estimate.totalCents <= 0 || !requirementsMet || (checkoutResult?.status === 'pending');

  const handleCheckout = async () => {
    if (!businessId) {
      setError('Business ID is required.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = {
        business_id: businessId,
        booking_id: bookingId || undefined,
        currency,
        line_items: estimate.lineItems.map((item) => ({
          name: item.name,
          amount_cents: item.amountCents,
          category: item.category,
        })),
      };
      const res = await fetch('/api/v1/platform/payments/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`Checkout failed (${res.status})`);
      }
      const data = await res.json();
      setCheckoutResult({
        paymentId: data.payment_id,
        status: data.status,
        receiptUrl: data.receipt_url,
        clientSecret: data.client_secret,
        refundedAmountCents: data.refunded_amount_cents,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to complete checkout');
    } finally {
      setLoading(false);
    }
  };

  const handleRefund = async () => {
    if (!checkoutResult?.paymentId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = {
        business_id: businessId,
        booking_id: bookingId || undefined,
        currency,
        line_items: estimate.lineItems.map((item) => ({
          name: item.name,
          amount_cents: item.amountCents,
          category: item.category,
        })),
        initiate_refund: true,
        payment_id: checkoutResult.paymentId,
      };
      const res = await fetch('/api/v1/platform/payments/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`Refund failed (${res.status})`);
      }
      const data = await res.json();
      setCheckoutResult((prev) =>
        prev
          ? {
              ...prev,
              status: data.status,
              refundedAmountCents: data.refunded_amount_cents,
            }
          : prev
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to initiate refund');
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
    <div className="space-y-6 p-4">
      <header className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">{copy.title}</h1>
            <p className="text-sm text-slate-500">{copy.subtitle}</p>
          </div>
          <label className="text-sm text-slate-600">
            {copy.localeLabel}
            <select
              className="ml-2 rounded-md border border-slate-200 px-2 py-1 text-sm"
              value={locale}
              onChange={(event) => setLocale(event.target.value)}
            >
              {copy.localeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="text-sm text-slate-600">
            {copy.businessLabel}
            <input
              className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              value={businessId}
              onChange={(event) => setBusinessId(event.target.value)}
              placeholder="UUID"
            />
          </label>
          <label className="text-sm text-slate-600">
            {copy.bookingLabel}
            <input
              className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              value={bookingId}
              onChange={(event) => setBookingId(event.target.value)}
              placeholder="Optional"
            />
          </label>
        </div>
      </header>

      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</p>}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <header className="mb-3">
              <h2 className="text-lg font-semibold text-slate-900">{copy.requirementsTitle}</h2>
              <p className="text-sm text-slate-500">{copy.requirementsGate}</p>
            </header>
            {businessId ? (
              <RequirementsChecklist
                businessId={businessId}
                onStatusChange={(nextRequirements, score) => {
                  setRequirements(nextRequirements);
                  setReadinessScore(score);
                }}
              />
            ) : (
              <p className="text-sm text-slate-500">Enter a business ID to load readiness.</p>
            )}
            <p className={`mt-3 text-sm ${requirementsMet ? 'text-emerald-600' : 'text-amber-600'}`}>
              {requirementsMet ? copy.readyMessage : copy.requirementsGate}
            </p>
          </article>

          <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <header className="mb-3">
              <h2 className="text-lg font-semibold text-slate-900">{copy.feesTitle}</h2>
              <p className="text-sm text-slate-500">Add all fees before collecting payment.</p>
            </header>
            <FeeEstimator
              currency={currency}
              onEstimate={(summary) => {
                setEstimate(summary);
              }}
            />
          </article>
        </div>

        <article className="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <header className="mb-3">
            <h2 className="text-lg font-semibold text-slate-900">{copy.paymentTitle}</h2>
            <p className="text-sm text-slate-500">Itemized total: {(estimate.totalCents / 100).toLocaleString(undefined, { style: 'currency', currency: currency.toUpperCase() })}</p>
          </header>

          <div className="flex-1 space-y-3 text-sm text-slate-600">
            <p>
              <strong>Status:</strong>{' '}
              {checkoutResult ? checkoutResult.status : 'Not started'}
            </p>
            {checkoutResult?.clientSecret && (
              <p>
                <strong>Client secret:</strong> {checkoutResult.clientSecret}
              </p>
            )}
            {checkoutResult?.receiptUrl && (
              <p>
                <strong>{copy.receiptLabel}:</strong>{' '}
                <a className="text-emerald-600 underline" href={checkoutResult.receiptUrl} target="_blank" rel="noreferrer">
                  {checkoutResult.receiptUrl}
                </a>
              </p>
            )}
            {checkoutResult?.refundedAmountCents ? (
              <p>
                <strong>Refunded:</strong> {(checkoutResult.refundedAmountCents / 100).toLocaleString(undefined, {
                  style: 'currency',
                  currency: currency.toUpperCase(),
                })}
              </p>
            ) : null}
            <p className="text-xs text-slate-400">{copy.refundNotice}</p>
          </div>

          <div className="mt-4 flex flex-col gap-3">
            <button
              type="button"
              onClick={handleCheckout}
              disabled={confirmDisabled}
              className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-300"
            >
              {loading && !checkoutResult ? 'Processing…' : copy.confirmCta}
            </button>
            <button
              type="button"
              onClick={handleRefund}
              disabled={!checkoutResult?.paymentId || loading}
              className="rounded-md border border-emerald-500 px-4 py-2 text-sm font-semibold text-emerald-600 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
            >
              {copy.refundCta}
            </button>
          </div>
        </article>
      </section>
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
