import { useEffect, useMemo, useState } from 'react';

import type { BusinessReadinessResponse } from './types';

type RequirementsChecklistStepProps = {
  businessId: string;
  onContinue: () => void;
  onLoaded?: (readiness: BusinessReadinessResponse) => void;
};

const statusStyles: Record<string, string> = {
  complete: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  in_review: 'bg-amber-50 border-amber-200 text-amber-700',
  missing: 'bg-rose-50 border-rose-200 text-rose-700',
};

const readinessCopy: Record<string, string> = {
  ready: 'You have satisfied the critical onboarding requirements. Continue to fee estimation to confirm pricing.',
  in_progress: 'A few regulatory tasks remain. We will highlight them below so you can resolve them before checkout.',
  not_ready: 'Key requirements are missing. Complete them to unlock booking and payment features.',
};

export default function RequirementsChecklistStep({
  businessId,
  onContinue,
  onLoaded,
}: RequirementsChecklistStepProps) {
  const [readiness, setReadiness] = useState<BusinessReadinessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/v1/platform/business/${businessId}/readiness`);
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const data: BusinessReadinessResponse = await response.json();
        if (cancelled) return;
        setReadiness(data);
        onLoaded?.(data);
      } catch (err) {
        if (!cancelled) {
          setError('Unable to load readiness checklist. Try again or contact support.');
          console.error(err);
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
  }, [businessId, onLoaded]);

  const readinessNarrative = useMemo(() => {
    if (!readiness) return '';
    return readinessCopy[readiness.readiness_stage] ?? readinessCopy.not_ready;
  }, [readiness]);

  const progressPercent = useMemo(() => {
    if (!readiness) return 0;
    return Math.round(readiness.readiness_score * 100);
  }, [readiness]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-xl font-semibold">Step 1: Confirm your requirements</h2>
        <p className="text-sm text-slate-600">
          We automatically assess permits, licenses, and inspections linked to your business profile.
        </p>
      </header>

      {loading && <p className="text-sm text-slate-500">Fetching the latest readiness snapshot…</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}

      {readiness && (
        <div className="space-y-4">
          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500">Current readiness stage</p>
                <p className="text-lg font-semibold capitalize">{readiness.readiness_stage.replace('_', ' ')}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-slate-500">Progress</p>
                <p className="text-2xl font-bold text-slate-900">{progressPercent}%</p>
              </div>
            </div>
            <div className="mt-2 h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-emerald-500 transition-all"
                style={{ width: `${progressPercent}%` }}
                aria-hidden="true"
              />
            </div>
            <p className="mt-3 text-sm text-slate-600">{readinessNarrative}</p>
            {readiness.gating_requirements.length > 0 && (
              <p className="mt-2 text-sm text-amber-700">
                Outstanding before checkout: {readiness.gating_requirements.join(', ')}
              </p>
            )}
          </section>

          <section className="grid gap-3 md:grid-cols-3">
            {readiness.checklist.map((item) => (
              <article
                key={item.slug}
                className={`rounded-lg border p-4 shadow-sm transition ${statusStyles[item.status] ?? statusStyles.missing}`}
              >
                <h3 className="text-base font-semibold">{item.title}</h3>
                <p className="mt-1 text-sm">{item.description}</p>
                <p className="mt-2 inline-flex items-center rounded-full bg-white/60 px-3 py-1 text-xs font-semibold uppercase tracking-wide">
                  {item.status.replace('_', ' ')}
                </p>
                {item.completed_at && (
                  <p className="mt-2 text-xs text-slate-600">
                    Updated {new Date(item.completed_at).toLocaleString()}
                  </p>
                )}
              </article>
            ))}
          </section>
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onContinue}
          disabled={loading || !readiness}
          className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Continue to fee estimator
        </button>
      </div>
    </div>
  );
}
