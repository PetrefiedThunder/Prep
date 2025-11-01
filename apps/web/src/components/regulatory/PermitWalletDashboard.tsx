import { useEffect, useMemo, useState } from 'react';

import type { BusinessReadinessResponse } from '../onboarding/types';

type Permit = {
  id: string;
  business_id: string;
  name: string;
  permit_type: string;
  status: string;
  issued_on: string | null;
  expires_on: string | null;
  webhook_url: string | null;
  last_webhook_at: string | null;
  metadata: Record<string, unknown> | null;
};

type PermitWalletDashboardProps = {
  businessId: string;
  permitIds: string[];
  locale?: string;
};

const statusVariants: Record<string, string> = {
  active: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  expired: 'text-rose-700 bg-rose-50 border-rose-200',
  pending: 'text-amber-700 bg-amber-50 border-amber-200',
  revoked: 'text-rose-700 bg-rose-50 border-rose-200',
};

function formatDate(value: string | null, locale: string) {
  if (!value) return '—';
  const date = new Date(value);
  return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' });
}

export default function PermitWalletDashboard({ businessId, permitIds, locale = 'en-US' }: PermitWalletDashboardProps) {
  const [readiness, setReadiness] = useState<BusinessReadinessResponse | null>(null);
  const [permits, setPermits] = useState<Permit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reminderState, setReminderState] = useState<Record<string, 'idle' | 'sending' | 'sent' | 'error'>>({});

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const readinessResponse = await fetch(`/api/v1/platform/business/${businessId}/readiness`);
        if (!readinessResponse.ok) {
          throw new Error(`Failed readiness request: ${readinessResponse.status}`);
        }
        const readinessData: BusinessReadinessResponse = await readinessResponse.json();
        if (cancelled) return;
        setReadiness(readinessData);

        const permitResponses = await Promise.all(
          permitIds.map(async (id) => {
            const response = await fetch(`/api/v1/platform/permits/${id}`);
            if (!response.ok) {
              throw new Error(`Failed permit request ${id}: ${response.status}`);
            }
            const data = (await response.json()) as Permit;
            return data;
          })
        );
        if (cancelled) return;
        setPermits(permitResponses);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setError('Unable to load permit wallet. Please refresh or contact support.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [businessId, permitIds]);

  const items = useMemo(() => {
    return permits.map((permit) => {
      const expiresOn = permit.expires_on ? new Date(permit.expires_on) : null;
      const daysUntilExpiry = expiresOn ? Math.ceil((expiresOn.getTime() - Date.now()) / 86400000) : null;
      const variant = statusVariants[permit.status] ?? 'text-slate-700 bg-slate-50 border-slate-200';
      const dueSoon = typeof daysUntilExpiry === 'number' && daysUntilExpiry <= 45;
      return { permit, daysUntilExpiry, variant, dueSoon };
    });
  }, [permits]);

  const handleReminder = async (permit: Permit) => {
    if (!permit.id) return;
    setReminderState((state) => ({ ...state, [permit.id]: 'sending' }));
    try {
      if (permit.webhook_url) {
        await fetch(permit.webhook_url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ permit_id: permit.id, business_id: permit.business_id, triggered_at: new Date().toISOString() }),
          mode: 'no-cors',
        });
      }
      const now = new Date().toISOString();
      setPermits((current) =>
        current.map((item) =>
          item.id === permit.id
            ? {
                ...item,
                last_webhook_at: now,
              }
            : item
        )
      );
      setReminderState((state) => ({ ...state, [permit.id]: 'sent' }));
    } catch (err) {
      console.error(err);
      setReminderState((state) => ({ ...state, [permit.id]: 'error' }));
    }
  };

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-xl font-semibold">Permit wallet</h2>
        <p className="text-sm text-slate-600">
          Track renewals, status changes, and automated reminders wired to your compliance webhook endpoints.
        </p>
        {readiness && (
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Readiness score {Math.round(readiness.readiness_score * 100)}% · Stage {readiness.readiness_stage.replace('_', ' ')}
          </p>
        )}
      </header>

      {loading && <p className="text-sm text-slate-500">Loading permit data…</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}

      <section className="grid gap-4 md:grid-cols-2">
        {items.map(({ permit, daysUntilExpiry, variant, dueSoon }) => {
          const reminderStatus = reminderState[permit.id] ?? 'idle';
          return (
            <article key={permit.id} className={`rounded-lg border p-4 shadow-sm ${variant}`}>
              <header className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{permit.name}</h3>
                  <p className="text-xs uppercase tracking-wide text-slate-500">{permit.permit_type}</p>
                </div>
                <span className="inline-flex items-center rounded-full bg-white/70 px-3 py-1 text-xs font-semibold uppercase text-slate-700">
                  {permit.status}
                </span>
              </header>

              <dl className="mt-4 space-y-2 text-sm text-slate-700">
                <div className="flex justify-between">
                  <dt>Issued</dt>
                  <dd>{formatDate(permit.issued_on, locale)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Expires</dt>
                  <dd>
                    {formatDate(permit.expires_on, locale)}
                    {dueSoon && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-white/60 px-2 py-0.5 text-xs font-semibold text-amber-700">
                        Renew soon
                      </span>
                    )}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt>Webhook</dt>
                  <dd>{permit.webhook_url ? 'Configured' : 'Not set'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Last reminder</dt>
                  <dd>{formatDate(permit.last_webhook_at, locale)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Days remaining</dt>
                  <dd>{typeof daysUntilExpiry === 'number' ? daysUntilExpiry : '—'}</dd>
                </div>
              </dl>

              <div className="mt-4 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => handleReminder(permit)}
                  disabled={reminderStatus === 'sending'}
                  className="inline-flex items-center rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow disabled:cursor-not-allowed disabled:bg-slate-400"
                >
                  {reminderStatus === 'sending' ? 'Sending…' : 'Send reminder'}
                </button>
                {reminderStatus === 'sent' && (
                  <span className="text-xs font-medium text-emerald-700">Reminder dispatched</span>
                )}
                {reminderStatus === 'error' && (
                  <span className="text-xs font-medium text-rose-700">Reminder failed</span>
                )}
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}
