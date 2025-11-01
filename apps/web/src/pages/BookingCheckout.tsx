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
    } finally {
      setLoading(false);
    }
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
    </div>
  );
}
