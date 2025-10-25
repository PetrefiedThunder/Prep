import { useEffect, useMemo, useState } from 'react';

type Role = 'admin' | 'host' | 'renter' | 'government';

type RegulatoryStatus = {
  overall_status: string;
  score: number;
  last_updated: string;
  alerts_count: number;
  pending_documents: number;
};

type RegulatoryDocument = {
  id: string;
  name: string;
  status: string;
  owner: Role;
  due_date: string;
  submitted_at?: string | null;
};

type ComplianceHistoryEntry = {
  id: string;
  occurred_at: string;
  actor: Role;
  description: string;
};

type MonitoringAlert = {
  id: string;
  created_at: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  acknowledged: boolean;
};

type MonitoringStatus = {
  last_run: string;
  healthy: boolean;
  active_alerts: number;
};

type ComplianceCheckResult = {
  status: string;
  executed_at: string;
  report?: Record<string, unknown> | null;
};

type DashboardCache = {
  status: RegulatoryStatus | null;
  documents: RegulatoryDocument[];
  alerts: MonitoringAlert[];
  history: ComplianceHistoryEntry[];
  monitoring: MonitoringStatus | null;
};

const roleLabels: Record<Role, string> = {
  admin: 'Admin',
  host: 'Host',
  renter: 'Renter',
  government: 'Government Partner',
};

const roleHighlights: Record<Role, string[]> = {
  admin: [
    'Review pending document submissions from hosts and renters.',
    'Coordinate monitoring alerts with government partners.',
    'Trigger compliance checks before approving new kitchen listings.',
  ],
  host: [
    'Ensure all operational licenses remain active and renewed.',
    'Respond to compliance alerts related to your kitchens promptly.',
    'Provide updated inspection documentation when requested.',
  ],
  renter: [
    'Upload food handler certifications for all staff members.',
    'Track verification status prior to upcoming bookings.',
    'Address outstanding compliance checklist items before service.',
  ],
  government: [
    'Monitor aggregate compliance health across partner kitchens.',
    'Access audit trails for regulatory reporting.',
    'Respond to escalated alerts requiring government intervention.',
  ],
};

const severityStyles: Record<MonitoringAlert['severity'], string> = {
  info: 'bg-sky-50 border-sky-200 text-sky-900',
  warning: 'bg-amber-50 border-amber-200 text-amber-900',
  critical: 'bg-rose-50 border-rose-200 text-rose-900',
};

const cacheKeyForRole = (role: Role) => `regulatory-dashboard-cache::${role}`;

function formatDate(input?: string | null) {
  if (!input) return '—';
  const date = new Date(input);
  return date.toLocaleString();
}

async function fetchJson<T>(url: string, role: Role, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Role': role,
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(`${response.status}`);
  }
  return response.json() as Promise<T>;
}

export default function RegulatoryDashboard() {
  const [role, setRole] = useState<Role>('admin');
  const [status, setStatus] = useState<RegulatoryStatus | null>(null);
  const [documents, setDocuments] = useState<RegulatoryDocument[]>([]);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [history, setHistory] = useState<ComplianceHistoryEntry[]>([]);
  const [monitoringStatus, setMonitoringStatus] = useState<MonitoringStatus | null>(null);
  const [checkResult, setCheckResult] = useState<ComplianceCheckResult | null>(null);
  const [submissionLinks, setSubmissionLinks] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [alertsError, setAlertsError] = useState<string | null>(null);

  const canRunChecks = role === 'admin' || role === 'host';
  const canManageMonitoring = role === 'admin' || role === 'government';

  const documentHeaders = useMemo(() => ({
    'aria-label': `${roleLabels[role]} compliance documents`,
  }), [role]);

  useEffect(() => {
    const cached = sessionStorage.getItem(cacheKeyForRole(role));
    if (cached) {
      try {
        const parsed: DashboardCache = JSON.parse(cached);
        setStatus(parsed.status);
        setDocuments(parsed.documents);
        setAlerts(parsed.alerts);
        setHistory(parsed.history);
        setMonitoringStatus(parsed.monitoring);
      } catch (err) {
        console.warn('Unable to parse cached regulatory dashboard data', err);
      }
    }

    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      setAlertsError(null);
      let latestAlerts: MonitoringAlert[] = [];
      let latestMonitoring: MonitoringStatus | null = null;
      try {
        const [statusData, documentData, historyData] = await Promise.all([
          fetchJson<RegulatoryStatus>('/api/v1/regulatory/status', role),
          fetchJson<RegulatoryDocument[]>('/api/v1/regulatory/documents', role),
          fetchJson<{ items: ComplianceHistoryEntry[]; total: number }>(
            '/api/v1/regulatory/history',
            role,
          ),
        ]);
        if (cancelled) return;
        setStatus(statusData);
        setDocuments(documentData);
        setHistory(historyData.items);

        try {
          const alertsData = await fetchJson<MonitoringAlert[]>(
            '/api/v1/regulatory/monitoring/alerts',
            role,
          );
          if (!cancelled) {
            latestAlerts = alertsData;
            setAlerts(alertsData);
            setAlertsError(null);
          }
        } catch (err) {
          if (!cancelled) {
            setAlerts([]);
            if (err instanceof Error && err.message === '403') {
              setAlertsError('Alerts restricted for this role.');
            } else {
              setAlertsError('Unable to load monitoring alerts.');
            }
          }
        }

        try {
          const monitoringData = await fetchJson<MonitoringStatus>(
            '/api/v1/regulatory/monitoring/status',
            role,
          );
          if (!cancelled) {
            latestMonitoring = monitoringData;
            setMonitoringStatus(monitoringData);
          }
        } catch (err) {
          if (!cancelled) {
            setMonitoringStatus(null);
          }
        }

        sessionStorage.setItem(
          cacheKeyForRole(role),
          JSON.stringify({
            status: statusData,
            documents: documentData,
            alerts: latestAlerts,
            history: historyData.items,
            monitoring: latestMonitoring,
          }),
        );
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load regulatory data', err);
          setError('Unable to load regulatory data. Please retry.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [role]);

  const handleDocumentSubmit = async (document: RegulatoryDocument) => {
    const link = submissionLinks[document.id];
    if (!link) {
      setError('Provide a document link before submitting.');
      return;
    }
    try {
      const updated = await fetchJson<RegulatoryDocument>(
        '/api/v1/regulatory/documents/submit',
        role,
        {
          method: 'POST',
          body: JSON.stringify({ document_id: document.id, url: link }),
        },
      );
      setDocuments((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setSubmissionLinks((prev) => ({ ...prev, [document.id]: '' }));
      setError(null);
    } catch (err) {
      console.error('Failed to submit document', err);
      setError('Unable to submit document at this time.');
    }
  };

  const handleComplianceCheck = async () => {
    if (!canRunChecks) return;
    try {
      const result = await fetchJson<ComplianceCheckResult>(
        '/api/v1/regulatory/check',
        role,
        {
          method: 'POST',
          body: JSON.stringify({
            scope: 'full',
            kitchen_payload: {
              license_info: { id: 'demo', status: 'active' },
              inspection_history: [],
            },
          }),
        },
      );
      setCheckResult(result);
      setError(null);
    } catch (err) {
      console.error('Failed to run compliance check', err);
      setError('Compliance check could not be completed.');
    }
  };

  return (
    <section className="flex flex-col gap-6" aria-label="Regulatory compliance dashboard">
      <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Regulatory Compliance</h1>
          <p className="text-slate-600">
            Centralized oversight for compliance, monitoring, and stakeholder collaboration.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Select stakeholder view">
          {(Object.keys(roleLabels) as Role[]).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRole(r)}
              className={`px-4 py-2 rounded-full border transition focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                role === r
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-indigo-700 border-indigo-200 hover:border-indigo-400'
              }`}
            >
              {roleLabels[r]}
            </button>
          ))}
        </div>
      </header>

      {error && (
        <div
          role="alert"
          className="border border-rose-200 bg-rose-50 text-rose-800 rounded-md p-4"
        >
          {error}
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-live="polite">
        <article className="rounded-lg bg-white shadow p-4 border border-slate-200">
          <p className="text-sm text-slate-500">Overall Status</p>
          <p className="text-xl font-semibold text-slate-900">
            {status ? status.overall_status.replace(/_/g, ' ') : loading ? 'Loading…' : '—'}
          </p>
        </article>
        <article className="rounded-lg bg-white shadow p-4 border border-slate-200">
          <p className="text-sm text-slate-500">Compliance Score</p>
          <p className="text-xl font-semibold text-emerald-600">
            {status ? `${status.score.toFixed(1)}%` : loading ? 'Loading…' : '—'}
          </p>
        </article>
        <article className="rounded-lg bg-white shadow p-4 border border-slate-200">
          <p className="text-sm text-slate-500">Active Alerts</p>
          <p className="text-xl font-semibold text-amber-600">
            {status ? status.alerts_count : alerts.length}
          </p>
        </article>
        <article className="rounded-lg bg-white shadow p-4 border border-slate-200">
          <p className="text-sm text-slate-500">Pending Documents</p>
          <p className="text-xl font-semibold text-rose-600">
            {status ? status.pending_documents : documents.filter((d) => d.status !== 'approved').length}
          </p>
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-3" aria-live="polite">
        <div className="lg:col-span-2 flex flex-col gap-4">
          <article className="rounded-lg bg-white shadow border border-slate-200 p-4" aria-labelledby="documents-heading">
            <div className="flex items-center justify-between gap-2">
              <h2 id="documents-heading" className="text-lg font-semibold text-slate-900">
                Document Submission & Tracking
              </h2>
              <span className="text-sm text-slate-500">Role: {roleLabels[role]}</span>
            </div>
            <div className="overflow-x-auto" {...documentHeaders}>
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Document
                    </th>
                    <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Due
                    </th>
                    <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Status
                    </th>
                    <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {documents.length === 0 && (
                    <tr>
                      <td className="px-3 py-4 text-sm text-slate-500" colSpan={4}>
                        No documents required for this role.
                      </td>
                    </tr>
                  )}
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50">
                      <td className="px-3 py-2 text-sm font-medium text-slate-900">{doc.name}</td>
                      <td className="px-3 py-2 text-sm text-slate-600">{formatDate(doc.due_date)}</td>
                      <td className="px-3 py-2 text-sm text-slate-600">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                            doc.status === 'approved'
                              ? 'bg-emerald-100 text-emerald-800'
                              : doc.status === 'submitted'
                              ? 'bg-indigo-100 text-indigo-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {doc.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-sm text-slate-600">
                        {doc.status === 'approved' ? (
                          <span className="text-emerald-600">Completed</span>
                        ) : (
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                            <label className="sr-only" htmlFor={`link-${doc.id}`}>
                              Provide submission link for {doc.name}
                            </label>
                            <input
                              id={`link-${doc.id}`}
                              name={`link-${doc.id}`}
                              type="url"
                              inputMode="url"
                              required
                              placeholder="https://"
                              className="w-full rounded border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                              value={submissionLinks[doc.id] ?? ''}
                              onChange={(event) =>
                                setSubmissionLinks((prev) => ({
                                  ...prev,
                                  [doc.id]: event.target.value,
                                }))
                              }
                              disabled={role !== doc.owner && role !== 'admin'}
                            />
                            <button
                              type="button"
                              className="rounded bg-indigo-600 px-3 py-1 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                              onClick={() => handleDocumentSubmit(doc)}
                              disabled={role !== doc.owner && role !== 'admin'}
                            >
                              Submit
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="rounded-lg bg-white shadow border border-slate-200 p-4" aria-labelledby="history-heading">
            <h2 id="history-heading" className="text-lg font-semibold text-slate-900">
              Compliance History & Audit Trail
            </h2>
            <ul className="mt-3 space-y-3">
              {history.length === 0 && (
                <li className="text-sm text-slate-500">No audit events recorded.</li>
              )}
              {history.map((entry) => (
                <li key={entry.id} className="rounded border border-slate-200 p-3">
                  <p className="text-sm font-semibold text-slate-900">
                    {formatDate(entry.occurred_at)} · {roleLabels[entry.actor]}
                  </p>
                  <p className="text-sm text-slate-600">{entry.description}</p>
                </li>
              ))}
            </ul>
          </article>
        </div>

        <aside className="flex flex-col gap-4">
          <article className="rounded-lg bg-white shadow border border-slate-200 p-4" aria-labelledby="alerts-heading">
            <div className="flex items-center justify-between gap-2">
              <h2 id="alerts-heading" className="text-lg font-semibold text-slate-900">
                Real-time Alerts
              </h2>
              {canManageMonitoring && monitoringStatus && (
                <span className="text-xs text-slate-500">
                  Last run {formatDate(monitoringStatus.last_run)}
                </span>
              )}
            </div>
            {alertsError && <p className="text-sm text-amber-700">{alertsError}</p>}
            <ul className="mt-3 space-y-3" aria-live="polite">
              {alerts.length === 0 && !alertsError && (
                <li className="text-sm text-slate-500">No active alerts.</li>
              )}
              {alerts.map((alert) => (
                <li
                  key={alert.id}
                  className={`rounded border p-3 text-sm ${severityStyles[alert.severity]}`}
                >
                  <p className="font-semibold capitalize">{alert.severity} alert</p>
                  <p className="mt-1">{alert.message}</p>
                  <p className="mt-1 text-xs opacity-75">{formatDate(alert.created_at)}</p>
                </li>
              ))}
            </ul>
            {canManageMonitoring && monitoringStatus && (
              <div className="mt-4 rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                <p className="font-semibold text-slate-900">Monitoring Status</p>
                <p>Healthy: {monitoringStatus.healthy ? 'Yes' : 'No'}</p>
                <p>Active alerts: {monitoringStatus.active_alerts}</p>
                <button
                  type="button"
                  className="mt-3 w-full rounded bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-slate-700"
                  onClick={() => {
                    fetchJson<MonitoringStatus>(
                      '/api/v1/regulatory/monitoring/run',
                      role,
                      {
                        method: 'POST',
                        body: JSON.stringify({ reason: 'Manual dashboard trigger' }),
                      },
                    )
                      .then((updated) => setMonitoringStatus(updated))
                      .catch(() => setAlertsError('Failed to trigger monitoring.'));
                  }}
                >
                  Run monitoring now
                </button>
              </div>
            )}
          </article>

          <article className="rounded-lg bg-white shadow border border-slate-200 p-4" aria-labelledby="check-heading">
            <h2 id="check-heading" className="text-lg font-semibold text-slate-900">
              Automated Compliance Check
            </h2>
            <p className="text-sm text-slate-600">
              Execute the Prep compliance engine for the selected stakeholder scope.
            </p>
            <button
              type="button"
              onClick={handleComplianceCheck}
              disabled={!canRunChecks}
              className="mt-3 w-full rounded bg-indigo-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {canRunChecks ? 'Run compliance check' : 'Checks restricted for this role'}
            </button>
            {checkResult && (
              <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                <p className="font-semibold text-slate-900">Last check</p>
                <p>Status: {checkResult.status}</p>
                <p>Executed: {formatDate(checkResult.executed_at)}</p>
                {checkResult.report && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-indigo-600">View engine output</summary>
                    <pre className="mt-2 overflow-x-auto rounded bg-slate-900 p-2 text-xs text-slate-100">
                      {JSON.stringify(checkResult.report, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </article>

          <article className="rounded-lg bg-white shadow border border-slate-200 p-4" aria-labelledby="role-highlights">
            <h2 id="role-highlights" className="text-lg font-semibold text-slate-900">
              Key actions for {roleLabels[role]}
            </h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-600">
              {roleHighlights[role].map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </aside>
      </section>
    </section>
  );
}
