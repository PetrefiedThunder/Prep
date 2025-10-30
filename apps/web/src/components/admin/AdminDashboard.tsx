import { useCallback, useEffect, useMemo, useState } from 'react';

import IntegrationManager from '../integration/Manager';
import { FEATURE_FLAGS } from '../../lib/featureFlags';

// Types mirrored from the admin API responses.
type ModerationDecision = 'approve' | 'reject' | 'request_changes';

type KitchenSummary = {
  id: string;
  name: string;
  owner_id: string;
  owner_email: string;
  owner_name: string;
  location: string | null;
  submitted_at: string;
  moderation_status: string;
  certification_status: string;
  trust_score: number | null;
  hourly_rate: string | number | null;
  moderated_at: string | null;
};

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

type KitchenListResponse = {
  items: KitchenSummary[];
  pagination: PaginationMeta;
};

type CertificationListResponse = {
  items: CertificationSummary[];
  pagination: PaginationMeta;
};

type KitchenModerationStats = {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  changes_requested: number;
  approvals_last_7_days: number;
};

type CertificationStats = {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  expiring_soon: number;
};

type UserStats = {
  total: number;
  active: number;
  suspended: number;
  admins: number;
  hosts: number;
};

type UserSummary = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_suspended: boolean;
  suspension_reason: string | null;
  created_at: string;
  last_login_at: string | null;
};

type UserListResponse = {
  items: UserSummary[];
  pagination: PaginationMeta;
};

const moderationLabels: Record<ModerationDecision, string> = {
  approve: 'Approve',
  reject: 'Reject',
  request_changes: 'Request changes',
};

function formatDate(value: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `${response.status}`);
  }
  return (await response.json()) as T;
}

function StatsCard({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) {
  return (
    <div className="rounded-lg bg-white shadow p-4 border border-slate-200">
      <p className="text-sm font-medium text-slate-600">{title}</p>
      <p className="text-2xl font-semibold text-slate-900 mt-1">{value}</p>
      {subtitle ? <p className="text-xs text-slate-500 mt-1">{subtitle}</p> : null}
    </div>
  );
}

export default function AdminDashboard() {
  const [kitchens, setKitchens] = useState<KitchenSummary[]>([]);
  const [kitchenPagination, setKitchenPagination] = useState<PaginationMeta | null>(null);
  const [certifications, setCertifications] = useState<CertificationSummary[]>([]);
  const [certPagination, setCertPagination] = useState<PaginationMeta | null>(null);
  const [userSummaries, setUserSummaries] = useState<UserSummary[]>([]);
  const [userPagination, setUserPagination] = useState<PaginationMeta | null>(null);
  const [moderationStats, setModerationStats] = useState<KitchenModerationStats | null>(null);
  const [certStats, setCertStats] = useState<CertificationStats | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [moderationNotes, setModerationNotes] = useState<Record<string, string>>({});
  const [certRejections, setCertRejections] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const hasQueues = useMemo(() => kitchens.length > 0 || certifications.length > 0, [kitchens, certifications]);

  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [kitchenResponse, certResponse, moderationStatsResponse, certStatsResponse, userStatsResponse, usersResponse] =
        await Promise.all([
          apiRequest<KitchenListResponse>('/api/v1/admin/kitchens/pending'),
          apiRequest<CertificationListResponse>('/api/v1/admin/certifications/pending'),
          apiRequest<KitchenModerationStats>('/api/v1/admin/kitchens/stats'),
          apiRequest<CertificationStats>('/api/v1/admin/certifications/stats'),
          apiRequest<UserStats>('/api/v1/admin/users/stats'),
          apiRequest<UserListResponse>('/api/v1/admin/users?limit=10'),
        ]);

      setKitchens(kitchenResponse.items);
      setKitchenPagination(kitchenResponse.pagination);
      setCertifications(certResponse.items);
      setCertPagination(certResponse.pagination);
      setModerationStats(moderationStatsResponse);
      setCertStats(certStatsResponse);
      setUserStats(userStatsResponse);
      setUserSummaries(usersResponse.items);
      setUserPagination(usersResponse.pagination);
    } catch (err) {
      console.error('Failed to load admin dashboard data', err);
      setError('Unable to load admin dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

  const handleModeration = useCallback(
    async (kitchenId: string, decision: ModerationDecision) => {
      setActionMessage(null);
      try {
        const payload: { action: ModerationDecision; reason?: string } = {
          action: decision,
        };
        if (decision !== 'approve' && moderationNotes[kitchenId]) {
          payload.reason = moderationNotes[kitchenId];
        }
        const response = await apiRequest<{ message: string }>(
          `/api/v1/admin/kitchens/${kitchenId}/moderate`,
          {
            method: 'POST',
            body: JSON.stringify(payload),
          },
        );
        setActionMessage(response.message);
        setModerationNotes((current) => {
          const next = { ...current };
          delete next[kitchenId];
          return next;
        });
        setKitchens((current) => current.filter((item) => item.id !== kitchenId));
        void refreshData();
      } catch (err) {
        console.error('Moderation action failed', err);
        setActionMessage('Moderation action failed. Please review and try again.');
      }
    },
    [moderationNotes, refreshData],
  );

  const handleCertificationDecision = useCallback(
    async (certId: string, approve: boolean) => {
      setActionMessage(null);
      try {
        const payload: { approve: boolean; rejection_reason?: string } = { approve };
        if (!approve) {
          payload.rejection_reason = certRejections[certId] || 'Rejected by administrator';
        }
        const response = await apiRequest<{ message: string }>(
          `/api/v1/admin/certifications/${certId}/verify`,
          {
            method: 'POST',
            body: JSON.stringify(payload),
          },
        );
        setActionMessage(response.message);
        setCertRejections((current) => {
          const next = { ...current };
          delete next[certId];
          return next;
        });
        setCertifications((current) => current.filter((item) => item.id !== certId));
        void refreshData();
      } catch (err) {
        console.error('Certification decision failed', err);
        setActionMessage('Certification decision failed. Please try again.');
      }
    },
    [certRejections, refreshData],
  );

  if (loading) {
    return <div className="p-6 text-slate-600">Loading admin dashboard…</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded border border-rose-200 bg-rose-50 p-4 text-rose-900">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold text-slate-900">Admin moderation & certification</h1>
        <p className="text-slate-600">
          Review pending kitchens, verify regulatory documentation, and keep the platform operating safely.
        </p>
      </header>

      {actionMessage ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-emerald-900">{actionMessage}</div>
      ) : null}

      <section>
        <h2 className="text-xl font-semibold text-slate-900">Operational summary</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {moderationStats ? (
            <StatsCard
              title="Moderation queue"
              value={`${moderationStats.pending} pending`}
              subtitle={`Approved last 7 days: ${moderationStats.approvals_last_7_days}`}
            />
          ) : null}
          {certStats ? (
            <StatsCard
              title="Certifications"
              value={`${certStats.pending} pending`}
              subtitle={`Expiring soon: ${certStats.expiring_soon}`}
            />
          ) : null}
          {userStats ? (
            <StatsCard
              title="Active users"
              value={`${userStats.active} of ${userStats.total}`}
              subtitle={`Admins: ${userStats.admins} · Hosts: ${userStats.hosts}`}
            />
          ) : null}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-900">Pending kitchens</h2>
          <p className="text-sm text-slate-500">
            {kitchenPagination ? `${kitchenPagination.total} waiting review` : 'No queue data'}
          </p>
        </div>
        {kitchens.length === 0 ? (
          <div className="rounded border border-slate-200 bg-white p-4 text-slate-500">No kitchens awaiting moderation.</div>
        ) : (
          <div className="space-y-4">
            {kitchens.map((kitchen) => (
              <div key={kitchen.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">{kitchen.name}</h3>
                    <p className="text-sm text-slate-600">
                      Host: {kitchen.owner_name} · {kitchen.owner_email}
                    </p>
                    <p className="text-sm text-slate-500">
                      Submitted {formatDate(kitchen.submitted_at)} · Trust score:{' '}
                      {kitchen.trust_score ?? '—'} · Hourly rate: {kitchen.hourly_rate ?? '—'}
                    </p>
                    <p className="text-sm text-slate-500">
                      Certification status: {kitchen.certification_status}
                    </p>
                  </div>
                  <div className="flex flex-col items-stretch gap-2 md:w-64">
                    <textarea
                      value={moderationNotes[kitchen.id] ?? ''}
                      onChange={(event) =>
                        setModerationNotes((current) => ({ ...current, [kitchen.id]: event.target.value }))
                      }
                      placeholder="Add moderation notes (required for rejections or changes)"
                      className="rounded border border-slate-300 p-2 text-sm"
                    />
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                      {(Object.keys(moderationLabels) as ModerationDecision[]).map((decision) => (
                        <button
                          key={decision}
                          type="button"
                          onClick={() => handleModeration(kitchen.id, decision)}
                          className="rounded bg-slate-900 px-2 py-1 text-sm font-medium text-white hover:bg-slate-700"
                        >
                          {moderationLabels[decision]}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-900">Certification reviews</h2>
          <p className="text-sm text-slate-500">
            {certPagination ? `${certPagination.total} documents to process` : 'No queue data'}
          </p>
        </div>
        {certifications.length === 0 ? (
          <div className="rounded border border-slate-200 bg-white p-4 text-slate-500">No pending certifications.</div>
        ) : (
          <div className="space-y-4">
            {certifications.map((cert) => (
              <div key={cert.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">{cert.kitchen_name}</h3>
                    <p className="text-sm text-slate-600">{cert.document_type}</p>
                    <a
                      href={cert.document_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-sky-700 hover:underline"
                    >
                      View document
                    </a>
                    <p className="text-sm text-slate-500">Submitted {formatDate(cert.submitted_at)}</p>
                  </div>
                  <div className="flex w-full flex-col gap-2 md:w-72">
                    <textarea
                      value={certRejections[cert.id] ?? ''}
                      onChange={(event) =>
                        setCertRejections((current) => ({ ...current, [cert.id]: event.target.value }))
                      }
                      placeholder="Add rejection reason"
                      className="rounded border border-slate-300 p-2 text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleCertificationDecision(cert.id, true)}
                        className="flex-1 rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCertificationDecision(cert.id, false)}
                        className="flex-1 rounded bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-500"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {FEATURE_FLAGS.INTEGRATIONS_BETA ? <IntegrationManager /> : null}

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-900">Recently active users</h2>
        {userSummaries.length === 0 ? (
          <div className="rounded border border-slate-200 bg-white p-4 text-slate-500">No users found.</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 font-medium text-slate-600">Name</th>
                  <th className="px-4 py-2 font-medium text-slate-600">Email</th>
                  <th className="px-4 py-2 font-medium text-slate-600">Role</th>
                  <th className="px-4 py-2 font-medium text-slate-600">Status</th>
                  <th className="px-4 py-2 font-medium text-slate-600">Last login</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {userSummaries.map((user) => (
                  <tr key={user.id}>
                    <td className="px-4 py-2 text-slate-900">{user.full_name}</td>
                    <td className="px-4 py-2 text-slate-600">{user.email}</td>
                    <td className="px-4 py-2 text-slate-500">{user.role}</td>
                    <td className="px-4 py-2 text-slate-500">
                      {user.is_suspended ? 'Suspended' : user.is_active ? 'Active' : 'Inactive'}
                    </td>
                    <td className="px-4 py-2 text-slate-500">{formatDate(user.last_login_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {userPagination ? (
          <p className="text-xs text-slate-500">
            Showing {userSummaries.length} of {userPagination.total} users
          </p>
        ) : null}
      </section>

      {!hasQueues ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 p-4 text-emerald-800">
          All caught up! The moderation and certification queues are clear.
        </div>
      ) : null}
    </div>
  );
}
