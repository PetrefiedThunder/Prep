import { useCallback, useEffect, useMemo, useState } from 'react';

export type IntegrationStatus = {
  id: string;
  name: string;
  description?: string | null;
  connected: boolean;
  authStatus: 'connected' | 'expired' | 'revoked' | 'pending';
  lastSyncAt: string | null;
  health: 'healthy' | 'degraded' | 'down';
  lastEventAt?: string | null;
  issues?: string | null;
};

const statusColors: Record<IntegrationStatus['health'], string> = {
  healthy: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  degraded: 'bg-amber-100 text-amber-800 border-amber-200',
  down: 'bg-rose-100 text-rose-800 border-rose-200',
};

const authLabels: Record<IntegrationStatus['authStatus'], string> = {
  connected: 'Connected',
  expired: 'Token expired',
  revoked: 'Access revoked',
  pending: 'Action required',
};

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

async function fetchStatuses(signal?: AbortSignal): Promise<IntegrationStatus[]> {
  const response = await fetch('/api/v1/integrations/status', { signal });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }
  const payload = (await response.json()) as { integrations: IntegrationStatus[] } | IntegrationStatus[];
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload.integrations ?? [];
}

function HealthBadge({ status }: { status: IntegrationStatus['health'] }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusColors[status]}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function ConnectedBadge({ connected }: { connected: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
        connected
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
          : 'border-slate-200 bg-slate-50 text-slate-600'
      }`}
    >
      {connected ? 'Connected' : 'Disconnected'}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white p-12 text-center shadow-sm">
      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden>
          <path
            d="M12 3l9 6-3 2v6l-6 4-6-4v-6l-3-2z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-slate-900">No integrations connected yet</h3>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        Connect an application to begin synchronizing compliance and operational data. New integrations will
        appear here with their live health and authorization status.
      </p>
    </div>
  );
}

export default function IntegrationManager() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const load = useCallback(async (signal?: AbortSignal, options?: { showSkeleton?: boolean }) => {
    const showSkeleton = options?.showSkeleton ?? true;
    if (showSkeleton) {
      setLoading(true);
    }
    setError(null);
    try {
      const data = await fetchStatuses(signal);
      setIntegrations(data);
    } catch (err) {
      console.error('Failed to load integrations', err);
      setError(err instanceof Error ? err.message : 'Unable to load integrations');
    } finally {
      if (showSkeleton) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => {
      controller.abort();
    };
  }, [load]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await load(undefined, { showSkeleton: false });
    } catch (err) {
      console.error('Failed to refresh integrations', err);
      setError(err instanceof Error ? err.message : 'Unable to refresh integrations');
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  const unhealthyCount = useMemo(
    () => integrations.filter((integration) => integration.health !== 'healthy').length,
    [integrations],
  );

  return (
    <section className="mt-8 rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-5">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Integration Manager</h2>
          <p className="mt-1 text-sm text-slate-500">
            Monitor connection health, authorization state, and synchronization recency for every external partner.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {unhealthyCount > 0 ? (
            <span className="inline-flex items-center rounded-full bg-rose-50 px-3 py-1 text-xs font-medium text-rose-600">
              {unhealthyCount} integration{unhealthyCount === 1 ? '' : 's'} need attention
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => void handleRefresh()}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {refreshing ? (
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" aria-hidden>
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
              </svg>
            ) : (
              <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden>
                <path
                  d="M4 4v6h6M20 20v-6h-6M20 8a8 8 0 00-15.89-1M4 16a8 8 0 0015.89 1"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            Refresh
          </button>
        </div>
      </div>
      <div className="px-6 py-6">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="animate-pulse rounded-xl border border-slate-200 bg-slate-50 p-5">
                <div className="h-4 w-1/3 rounded bg-slate-200" />
                <div className="mt-2 h-3 w-1/4 rounded bg-slate-200" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
            <p className="font-medium">Unable to load integrations</p>
            <p className="mt-1 text-rose-600">{error}</p>
          </div>
        ) : integrations.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4">
            {integrations.map((integration) => (
              <article
                key={integration.id}
                className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md md:flex-row md:items-center md:justify-between"
              >
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-base font-semibold text-slate-900">{integration.name}</h3>
                    <ConnectedBadge connected={integration.connected} />
                    <HealthBadge status={integration.health} />
                  </div>
                  {integration.description ? (
                    <p className="mt-2 text-sm text-slate-500">{integration.description}</p>
                  ) : null}
                  {integration.issues ? (
                    <p className="mt-3 text-sm text-rose-600">{integration.issues}</p>
                  ) : null}
                </div>
                <dl className="grid w-full grid-cols-2 gap-4 text-sm text-slate-600 md:w-auto md:grid-cols-4">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Auth status</dt>
                    <dd className="mt-1 font-medium text-slate-800">{authLabels[integration.authStatus]}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Last sync</dt>
                    <dd className="mt-1 font-medium text-slate-800">{formatTimestamp(integration.lastSyncAt)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Last event</dt>
                    <dd className="mt-1 font-medium text-slate-800">{formatTimestamp(integration.lastEventAt)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Health</dt>
                    <dd className="mt-1 font-medium text-slate-800">{integration.health}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
