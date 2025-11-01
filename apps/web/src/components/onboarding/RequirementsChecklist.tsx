import { useCallback, useEffect, useMemo, useState } from 'react';

type Requirement = {
  name: string;
  description?: string | null;
  status: string;
  completedAt?: string | null;
};

type ChecklistResponse = {
  readiness_score: number;
  readinessScore?: number;
  requirements: Requirement[];
};

const STATUS_COPY: Record<string, string> = {
  pending: 'Pending',
  submitted: 'Submitted for review',
  approved: 'Approved',
  completed: 'Completed',
  complete: 'Completed',
  rejected: 'Needs attention',
};

type RequirementsChecklistProps = {
  businessId: string;
  pollIntervalMs?: number;
  className?: string;
  onStatusChange?: (requirements: Requirement[], readinessScore: number) => void;
};

function normalizeRequirementStatus(status: string | undefined): string {
  if (!status) {
    return 'pending';
  }
  return status.toLowerCase();
}

export function RequirementsChecklist({
  businessId,
  pollIntervalMs = 30000,
  className,
  onStatusChange,
}: RequirementsChecklistProps) {
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [readinessScore, setReadinessScore] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReadiness = useCallback(async () => {
    if (!businessId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/platform/business/${businessId}/readiness`);
      if (!res.ok) {
        throw new Error(`Failed to load readiness (${res.status})`);
      }
      const payload: ChecklistResponse = await res.json();
      const score = payload.readinessScore ?? payload.readiness_score ?? 0;
      const normalizedRequirements = (payload.requirements ?? []).map((item) => ({
        ...item,
        status: normalizeRequirementStatus(item.status),
      }));
      setRequirements(normalizedRequirements);
      setReadinessScore(score);
      onStatusChange?.(normalizedRequirements, score);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [businessId, onStatusChange]);

  useEffect(() => {
    void fetchReadiness();
  }, [fetchReadiness]);

  useEffect(() => {
    if (!pollIntervalMs) {
      return;
    }
    const id = window.setInterval(() => {
      void fetchReadiness();
    }, pollIntervalMs);
    return () => window.clearInterval(id);
  }, [fetchReadiness, pollIntervalMs]);

  const percentComplete = useMemo(() => Math.round(readinessScore * 100), [readinessScore]);

  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className ?? ''}`}>
      <header className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Requirements checklist</h2>
          <p className="text-sm text-slate-500">
            Track onboarding prerequisites pulled directly from your compliance workspace.
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-slate-600">Readiness</p>
          <p className="text-2xl font-bold text-emerald-600">{percentComplete}%</p>
        </div>
      </header>

      <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${percentComplete}%` }}
        />
      </div>

      {error && <p className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</p>}
      {loading && <p className="mb-3 text-sm text-slate-500">Refreshing status…</p>}

      <ul className="space-y-3">
        {requirements.map((req) => {
          const statusKey = normalizeRequirementStatus(req.status);
          const statusLabel = STATUS_COPY[statusKey] ?? statusKey;
          const completedAt = req.completedAt ?? (req as any).completed_at ?? null;
          return (
            <li key={req.name} className="flex items-start gap-3 rounded-md border border-slate-100 p-3">
              <span
                className={`mt-1 inline-flex h-2.5 w-2.5 shrink-0 rounded-full ${
                  statusKey === 'approved' || statusKey === 'completed' || statusKey === 'complete'
                    ? 'bg-emerald-500'
                    : statusKey === 'submitted'
                    ? 'bg-amber-400'
                    : statusKey === 'rejected'
                    ? 'bg-red-500'
                    : 'bg-slate-300'
                }`}
              />
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900">{req.name}</p>
                {req.description && <p className="text-sm text-slate-500">{req.description}</p>}
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
                    {statusLabel}
                  </span>
                  {completedAt && (
                    <time dateTime={completedAt} className="text-slate-400">
                      Completed {new Date(completedAt).toLocaleDateString()}
                    </time>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      <footer className="mt-4 flex items-center justify-between gap-2 text-sm text-slate-500">
        <span>Updated automatically every {Math.round(pollIntervalMs / 1000)}s</span>
        <button
          type="button"
          onClick={() => fetchReadiness()}
          className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
        >
          Refresh now
        </button>
      </footer>
    </section>
  );
}

export type { Requirement };
