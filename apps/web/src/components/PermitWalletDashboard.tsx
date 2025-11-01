import { useCallback, useEffect, useMemo, useState } from 'react';

type Permit = {
  id: string;
  permit_number: string;
  permit_type: string;
  jurisdiction?: string | null;
  status: string;
  expires_at?: string | null;
  issued_at?: string | null;
};

type ReadinessRequirement = {
  name: string;
  status: string;
  description?: string | null;
};

type ReadinessPayload = {
  permit_ids: string[];
  requirements: ReadinessRequirement[];
  readiness_score: number;
};

type ReminderEvent = {
  permitId: string;
  message: string;
  sendAt?: string;
};

type PermitWalletDashboardProps = {
  businessId: string;
  pollIntervalMs?: number;
  className?: string;
};

function normalizeStatus(status: string | undefined) {
  return (status ?? 'pending').toLowerCase();
}

function daysUntil(dateString: string | null | undefined): number | null {
  if (!dateString) {
    return null;
  }
  const expiresAt = new Date(dateString);
  if (Number.isNaN(expiresAt.getTime())) {
    return null;
  }
  const diffMs = expiresAt.getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

function usePermitReminderSubscription(businessId: string | null, onReminder: (event: ReminderEvent) => void) {
  useEffect(() => {
    if (!businessId || typeof window === 'undefined' || typeof EventSource === 'undefined') {
      return;
    }
    let isClosed = false;
    let source: EventSource | null = null;
    try {
      source = new EventSource(`/api/v1/platform/permits/reminders?business_id=${businessId}`);
      source.onmessage = (event) => {
        if (isClosed) {
          return;
        }
        try {
          const payload = JSON.parse(event.data) as ReminderEvent;
          onReminder(payload);
        } catch (err) {
          console.warn('Unable to parse reminder event', err);
        }
      };
      source.onerror = () => {
        source?.close();
      };
    } catch (err) {
      console.info('Permit reminder stream not available', err);
    }

    return () => {
      isClosed = true;
      source?.close();
    };
  }, [businessId, onReminder]);
}

export function PermitWalletDashboard({ businessId, pollIntervalMs = 60000, className }: PermitWalletDashboardProps) {
  const [permits, setPermits] = useState<Permit[]>([]);
  const [requirements, setRequirements] = useState<ReadinessRequirement[]>([]);
  const [readinessScore, setReadinessScore] = useState(0);
  const [reminders, setReminders] = useState<ReminderEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const readinessRes = await fetch(`/api/v1/platform/business/${businessId}/readiness`);
      if (!readinessRes.ok) {
        throw new Error(`Unable to load readiness (${readinessRes.status})`);
      }
      const readinessData: ReadinessPayload = await readinessRes.json();
      setRequirements(readinessData.requirements ?? []);
      setReadinessScore(readinessData.readiness_score ?? 0);

      const permitIds = readinessData.permit_ids ?? [];
      if (permitIds.length === 0) {
        setPermits([]);
      } else {
        const responses = await Promise.all(
          permitIds.map(async (id) => {
            const res = await fetch(`/api/v1/platform/permits/${id}`);
            if (!res.ok) {
              throw new Error(`Permit ${id} could not be loaded (${res.status})`);
            }
            return res.json();
          })
        );
        setPermits(responses);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!pollIntervalMs) {
      return;
    }
    const id = window.setInterval(() => {
      void fetchData();
    }, pollIntervalMs);
    return () => window.clearInterval(id);
  }, [fetchData, pollIntervalMs]);

  usePermitReminderSubscription(
    businessId,
    useCallback(
      (event) => {
        setReminders((prev) => [event, ...prev].slice(0, 5));
      },
      []
    )
  );

  const readinessPercent = useMemo(() => Math.round((readinessScore ?? 0) * 100), [readinessScore]);

  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className ?? ''}`}>
      <header className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Permit wallet</h2>
          <p className="text-sm text-slate-500">Centralize permits, monitor expirations, and trigger renewal reminders.</p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wide text-slate-500">Readiness</p>
          <p className="text-2xl font-semibold text-emerald-600">{readinessPercent}%</p>
        </div>
      </header>

      {error && <p className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</p>}
      {loading && <p className="mb-3 text-sm text-slate-500">Syncing permits…</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-700">Active permits</h3>
          <ul className="mt-2 space-y-3">
            {permits.map((permit) => {
              const status = normalizeStatus(permit.status);
              const days = daysUntil(permit.expires_at ?? null);
              const isExpired = days !== null && days < 0;
              const isExpiringSoon = days !== null && days >= 0 && days <= 30;
              return (
                <li key={permit.id} className="rounded-md border border-slate-100 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{permit.permit_type}</p>
                      <p className="text-xs text-slate-500">Permit #{permit.permit_number}</p>
                    </div>
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        status === 'active'
                          ? 'bg-emerald-100 text-emerald-700'
                          : status === 'expired'
                          ? 'bg-red-100 text-red-600'
                          : status === 'pending'
                          ? 'bg-amber-100 text-amber-600'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {status}
                    </span>
                  </div>
                  <div className="mt-2 grid gap-2 text-xs text-slate-500 md:grid-cols-3">
                    <span>Jurisdiction: {permit.jurisdiction ?? '—'}</span>
                    <span>Issued: {permit.issued_at ? new Date(permit.issued_at).toLocaleDateString() : 'Pending'}</span>
                    <span>
                      Expires:{' '}
                      {permit.expires_at ? new Date(permit.expires_at).toLocaleDateString() : '—'}
                      {isExpired && <strong className="ml-1 text-red-600">Expired</strong>}
                      {!isExpired && isExpiringSoon && <strong className="ml-1 text-amber-600">Renew soon</strong>}
                    </span>
                  </div>
                </li>
              );
            })}
            {permits.length === 0 && (
              <li className="rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                No permits on file yet. Upload documentation to populate your wallet.
              </li>
            )}
          </ul>
        </div>

        <div className="space-y-4">
          <div className="rounded-md border border-slate-100 p-3">
            <h3 className="text-sm font-semibold text-slate-700">Upcoming reminders</h3>
            <ul className="mt-2 space-y-2 text-xs text-slate-500">
              {reminders.length > 0 ? (
                reminders.map((reminder, index) => (
                  <li key={`${reminder.permitId}-${index}`} className="rounded bg-slate-50 px-2 py-2">
                    <p className="font-medium text-slate-600">Permit {reminder.permitId}</p>
                    <p>{reminder.message}</p>
                    {reminder.sendAt && <p className="text-[10px] text-slate-400">{new Date(reminder.sendAt).toLocaleString()}</p>}
                  </li>
                ))
              ) : (
                <li className="rounded bg-slate-50 px-2 py-2">Webhook reminders will appear here once subscribed.</li>
              )}
            </ul>
          </div>

          <div className="rounded-md border border-slate-100 p-3">
            <h3 className="text-sm font-semibold text-slate-700">Readiness blockers</h3>
            <ul className="mt-2 space-y-2 text-xs text-slate-500">
              {requirements.map((req) => (
                <li key={req.name} className="rounded bg-white px-2 py-2 shadow-sm">
                  <p className="font-medium text-slate-700">{req.name}</p>
                  <p className="text-[11px] uppercase tracking-wide text-slate-400">{normalizeStatus(req.status)}</p>
                  {req.description && <p className="mt-1 text-slate-500">{req.description}</p>}
                </li>
              ))}
              {requirements.length === 0 && <li>No outstanding requirements 🎉</li>}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
