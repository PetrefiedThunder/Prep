import { useCallback, useEffect, useMemo, useState } from 'react';

type CertificationSummary = {
  id: string;
  kitchen_id: string;
  kitchen_name: string;
  document_type: string;
  document_url: string;
  status: string;
  submitted_at: string;
  verified_at: string | null;
  reviewer_id: string | null;
  rejection_reason: string | null;
  expires_at: string | null;
};

type PaginationMeta = {
  limit: number;
  offset: number;
  total: number;
};

type CertificationListResponse = {
  items: CertificationSummary[];
  pagination: PaginationMeta;
};

type DecisionState = 'idle' | 'loading';

const PAGE_SIZE = 10;

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

async function getPendingCertifications(offset: number): Promise<CertificationListResponse> {
  const response = await fetch(`/api/v1/admin/certifications/pending?limit=${PAGE_SIZE}&offset=${offset}`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to load pending verifications');
  }
  return (await response.json()) as CertificationListResponse;
}

async function submitDecision(
  certificationId: string,
  payload: { approve: boolean; rejection_reason?: string },
): Promise<string> {
  const response = await fetch(`/api/v1/admin/certifications/${certificationId}/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Verification request failed');
  }
  const data = (await response.json()) as { message?: string };
  return data.message ?? 'Verification saved successfully';
}

export default function AdminModerationPage() {
  const [certifications, setCertifications] = useState<CertificationSummary[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [decisionStatus, setDecisionStatus] = useState<Record<string, DecisionState>>({});
  const [decisionErrors, setDecisionErrors] = useState<Record<string, string>>({});
  const [rejectionReasons, setRejectionReasons] = useState<Record<string, string>>({});

  const totalPages = useMemo(() => {
    if (!pagination) return 1;
    if (pagination.total === 0) return 1;
    return Math.max(1, Math.ceil(pagination.total / pagination.limit));
  }, [pagination]);

  const currentPage = useMemo(() => {
    if (!pagination) return 1;
    return Math.floor(pagination.offset / pagination.limit) + 1;
  }, [pagination]);

  const loadCertifications = useCallback(async (nextOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPendingCertifications(nextOffset);
      setCertifications(data.items);
      setPagination(data.pagination);
      setOffset(data.pagination.offset);
    } catch (err) {
      console.error('Failed to load pending verifications', err);
      setError(err instanceof Error ? err.message : 'Unable to load pending verifications');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCertifications(0);
  }, [loadCertifications]);

  const handleRefresh = useCallback(async () => {
    await loadCertifications(offset);
  }, [loadCertifications, offset]);

  const setDecisionState = useCallback((certId: string, state: DecisionState) => {
    setDecisionStatus((current) => ({ ...current, [certId]: state }));
  }, []);

  const clearDecisionError = useCallback((certId: string) => {
    setDecisionErrors((current) => {
      if (!(certId in current)) return current;
      const { [certId]: _removed, ...rest } = current;
      return rest;
    });
  }, []);

  const handleDecision = useCallback(
    async (certificationId: string, approve: boolean) => {
      setFlashMessage(null);
      clearDecisionError(certificationId);
      if (!approve && !rejectionReasons[certificationId]) {
        setDecisionErrors((current) => ({
          ...current,
          [certificationId]: 'Please provide a rejection reason before submitting.',
        }));
        return;
      }

      setDecisionState(certificationId, 'loading');
      try {
        const message = await submitDecision(certificationId, {
          approve,
          rejection_reason: approve ? undefined : rejectionReasons[certificationId],
        });
        setFlashMessage(message);
        await handleRefresh();
      } catch (err) {
        console.error('Failed to submit verification decision', err);
        setDecisionErrors((current) => ({
          ...current,
          [certificationId]: err instanceof Error ? err.message : 'Unable to submit decision',
        }));
      } finally {
        setDecisionState(certificationId, 'idle');
      }
    },
    [clearDecisionError, handleRefresh, rejectionReasons, setDecisionState],
  );

  const handleReasonChange = useCallback((certId: string, value: string) => {
    setRejectionReasons((current) => ({ ...current, [certId]: value }));
    clearDecisionError(certId);
  }, [clearDecisionError]);

  const handleNextPage = useCallback(() => {
    if (!pagination) return;
    const nextOffset = pagination.offset + pagination.limit;
    if (nextOffset >= pagination.total) return;
    void loadCertifications(nextOffset);
  }, [loadCertifications, pagination]);

  const handlePreviousPage = useCallback(() => {
    if (!pagination) return;
    const nextOffset = Math.max(0, pagination.offset - pagination.limit);
    if (nextOffset === pagination.offset) return;
    void loadCertifications(nextOffset);
  }, [loadCertifications, pagination]);

  const hasItems = certifications.length > 0;
  const isBusy = loading;

  return (
    <div className="min-h-screen bg-slate-100 py-10 px-4">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="space-y-2">
          <h1 className="text-3xl font-semibold text-slate-900">Certification moderation</h1>
          <p className="text-slate-600">
            Review pending certification submissions and approve or reject them to keep the marketplace compliant.
          </p>
        </header>

        {flashMessage ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-700">{flashMessage}</div>
        ) : null}

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div>
        ) : null}

        <section className="rounded-lg border border-slate-200 bg-white shadow">
          <div className="flex items-center justify-between border-b border-slate-200 p-4">
            <h2 className="text-lg font-medium text-slate-900">Pending verifications</h2>
            <button
              type="button"
              className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => void handleRefresh()}
              disabled={isBusy}
            >
              Refresh
            </button>
          </div>

          {isBusy ? (
            <div className="p-6 text-sm text-slate-500">Loading pending verifications…</div>
          ) : null}

          {!isBusy && !hasItems ? (
            <div className="p-6 text-sm text-slate-500">No pending verifications right now.</div>
          ) : null}

          {!isBusy && hasItems ? (
            <ul className="divide-y divide-slate-200">
              {certifications.map((certification) => {
                const status = decisionStatus[certification.id] ?? 'idle';
                const decisionError = decisionErrors[certification.id];
                const rejectionReason = rejectionReasons[certification.id] ?? '';

                return (
                  <li key={certification.id} className="p-4">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-2">
                        <div>
                          <p className="text-base font-semibold text-slate-900">{certification.kitchen_name}</p>
                          <p className="text-sm text-slate-500">Document type: {certification.document_type}</p>
                        </div>
                        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm text-slate-600 md:grid-cols-2">
                          <div>
                            <dt className="font-medium text-slate-500">Submitted</dt>
                            <dd>{formatDate(certification.submitted_at)}</dd>
                          </div>
                          <div>
                            <dt className="font-medium text-slate-500">Current status</dt>
                            <dd className="capitalize">{certification.status.replaceAll('_', ' ')}</dd>
                          </div>
                          <div>
                            <dt className="font-medium text-slate-500">Document</dt>
                            <dd>
                              <a
                                href={certification.document_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-indigo-600 underline hover:text-indigo-500"
                              >
                                View file
                              </a>
                            </dd>
                          </div>
                        </dl>
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-slate-600" htmlFor={`rejection-${certification.id}`}>
                            Rejection reason (required to reject)
                          </label>
                          <textarea
                            id={`rejection-${certification.id}`}
                            value={rejectionReason}
                            onChange={(event) => handleReasonChange(certification.id, event.target.value)}
                            rows={3}
                            placeholder="Explain why this certification is being rejected"
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                          />
                        </div>
                        {decisionError ? <p className="text-sm text-rose-600">{decisionError}</p> : null}
                      </div>

                      <div className="flex flex-col gap-2 md:w-48">
                        <button
                          type="button"
                          onClick={() => void handleDecision(certification.id, true)}
                          disabled={status === 'loading'}
                          className="inline-flex items-center justify-center rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {status === 'loading' ? 'Saving…' : 'Approve'}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDecision(certification.id, false)}
                          disabled={status === 'loading'}
                          className="inline-flex items-center justify-center rounded-md border border-rose-400 bg-white px-3 py-2 text-sm font-semibold text-rose-600 shadow-sm hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {status === 'loading' ? 'Saving…' : 'Reject'}
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}

          {pagination ? (
            <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <button
                type="button"
                onClick={handlePreviousPage}
                disabled={isBusy || pagination.offset === 0}
                className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-700 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Previous
              </button>
              <span>
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                onClick={handleNextPage}
                disabled={
                  isBusy ||
                  pagination.offset + pagination.limit >= pagination.total
                }
                className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-700 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Next
              </button>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
