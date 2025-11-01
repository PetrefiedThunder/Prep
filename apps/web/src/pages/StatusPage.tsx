import { useEffect, useMemo, useState } from 'react';

interface SyntheticCheck {
  name: string;
  p95_ms: number;
  threshold_ms: number;
  status: 'pass' | 'fail' | string;
}

interface Incident {
  id: string;
  started_at: string;
  resolved_at?: string;
  severity: string;
  summary: string;
  root_cause?: string;
  remediations?: string[];
}

interface StatusDocument {
  generated_at: string;
  uptime?: {
    rolling_7d?: number;
    rolling_30d?: number;
  };
  checks: SyntheticCheck[];
  recent_incidents?: Incident[];
}

function formatPercent(value?: number) {
  return typeof value === 'number' ? `${value.toFixed(2)}%` : '—';
}

function formatLatency(value: number) {
  return `${value.toFixed(1)} ms`;
}

function formatTimestamp(value: string | undefined) {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export default function StatusPage() {
  const [document, setDocument] = useState<StatusDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const response = await fetch('/synthetics/status.json', {
          headers: { 'Accept': 'application/json' },
        });
        if (!response.ok) {
          throw new Error(`Failed to load status (HTTP ${response.status})`);
        }
        const payload: StatusDocument = await response.json();
        if (!cancelled) {
          setDocument(payload);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load status');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    const interval = window.setInterval(load, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const overallStatus = useMemo(() => {
    if (!document) {
      return 'unknown';
    }
    return document.checks.every((check) => check.status === 'pass') ? 'operational' : 'degraded';
  }, [document]);

  return (
    <div className="p-6 space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">Platform status</h1>
        <p className="text-slate-600">
          Synthetic monitors run continuously against San Francisco and Joshua Tree regulatory endpoints. Latency must remain
          under 200&nbsp;ms p95 to be considered healthy.
        </p>
        <StatusBadge status={overallStatus} />
        {document?.generated_at && (
          <p className="text-sm text-slate-500">Last updated {formatTimestamp(document.generated_at)}</p>
        )}
      </header>

      {loading && <p className="text-slate-500">Loading latest results…</p>}
      {error && <p className="text-red-600">{error}</p>}

      {document && !loading && (
        <div className="space-y-8">
          <section>
            <h2 className="text-xl font-semibold mb-2">Uptime</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <MetricCard label="Rolling 7d" value={formatPercent(document.uptime?.rolling_7d)} />
              <MetricCard label="Rolling 30d" value={formatPercent(document.uptime?.rolling_30d)} />
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-2">Endpoint health</h2>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-sm font-semibold text-slate-600">Check</th>
                    <th className="px-4 py-2 text-left text-sm font-semibold text-slate-600">p95 latency</th>
                    <th className="px-4 py-2 text-left text-sm font-semibold text-slate-600">Threshold</th>
                    <th className="px-4 py-2 text-left text-sm font-semibold text-slate-600">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {document.checks.map((check) => (
                    <tr key={check.name}>
                      <td className="px-4 py-2 text-sm font-medium text-slate-700">{check.name.replaceAll('_', ' ')}</td>
                      <td className="px-4 py-2 text-sm text-slate-600">{formatLatency(check.p95_ms)}</td>
                      <td className="px-4 py-2 text-sm text-slate-600">{formatLatency(check.threshold_ms)}</td>
                      <td className="px-4 py-2 text-sm">
                        <StatusBadge status={check.status === 'pass' ? 'operational' : 'degraded'} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-2">Recent incidents</h2>
            {document.recent_incidents && document.recent_incidents.length > 0 ? (
              <ul className="space-y-4">
                {document.recent_incidents.map((incident) => (
                  <li key={incident.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold text-slate-700">{incident.summary}</p>
                        <p className="text-xs text-slate-500">{incident.severity} • {incident.id}</p>
                      </div>
                      <StatusBadge status={incident.resolved_at ? 'operational' : 'degraded'} />
                    </div>
                    <dl className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-600 md:grid-cols-2">
                      <div>
                        <dt className="font-medium text-slate-700">Started</dt>
                        <dd>{formatTimestamp(incident.started_at)}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-slate-700">Resolved</dt>
                        <dd>{formatTimestamp(incident.resolved_at)}</dd>
                      </div>
                      {incident.root_cause && (
                        <div className="md:col-span-2">
                          <dt className="font-medium text-slate-700">Root cause</dt>
                          <dd>{incident.root_cause}</dd>
                        </div>
                      )}
                      {incident.remediations && incident.remediations.length > 0 && (
                        <div className="md:col-span-2">
                          <dt className="font-medium text-slate-700">Remediations</dt>
                          <dd>
                            <ul className="list-disc pl-5">
                              {incident.remediations.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </dd>
                        </div>
                      )}
                    </dl>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-500">No incidents recorded in the last 30 days.</p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const config = {
    operational: {
      label: 'Operational',
      className: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    },
    degraded: {
      label: 'Degraded',
      className: 'bg-amber-100 text-amber-700 border-amber-200',
    },
    unknown: {
      label: 'Unknown',
      className: 'bg-slate-100 text-slate-600 border-slate-200',
    },
  } as const;

  const variant = config[normalized as keyof typeof config] ?? config.unknown;

  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${variant.className}`}>
      {variant.label}
    </span>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-800">{value}</p>
    </div>
  );
}
