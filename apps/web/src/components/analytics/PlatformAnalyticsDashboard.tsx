import { useEffect, useState } from 'react';

type TimeSeriesData = {
  date: string;
  value: number | string;
};

type PlatformOverviewMetrics = {
  total_users: number;
  total_hosts: number;
  total_kitchens: number;
  active_kitchens: number;
  total_bookings: number;
  total_revenue: string | number;
  new_users_last_30_days: number;
  bookings_trend: TimeSeriesData[];
  revenue_trend: TimeSeriesData[];
};

type KitchenRevenue = {
  kitchen_id: string;
  kitchen_name: string;
  total_revenue: string | number;
  booking_count: number;
};

type PaymentMethodBreakdown = {
  method: string;
  percentage: number;
};

type RevenueAnalytics = {
  total_revenue: string | number;
  revenue_trends: TimeSeriesData[];
  revenue_by_kitchen: KitchenRevenue[];
  average_booking_value: string | number;
  revenue_forecast: TimeSeriesData[];
  payment_methods_breakdown: PaymentMethodBreakdown[];
};

type GrowthChannelBreakdown = {
  channel: string;
  signups: number;
  conversion_rate: number;
};

type PlatformGrowthMetrics = {
  user_signups: TimeSeriesData[];
  host_signups: TimeSeriesData[];
  conversion_rate: TimeSeriesData[];
  acquisition_channels: GrowthChannelBreakdown[];
};

type ModerationQueueMetrics = {
  pending: number;
  in_review: number;
  escalated: number;
  sla_breaches: number;
  average_review_time_hours: number;
  moderation_trend: TimeSeriesData[];
};

type AdminTeamMemberPerformance = {
  admin_id: string;
  admin_name: string;
  resolved_cases: number;
  average_resolution_time_hours: number;
  quality_score: number;
};

type AdminPerformanceMetrics = {
  total_resolved: number;
  backlog: number;
  productivity_trend: TimeSeriesData[];
  team: AdminTeamMemberPerformance[];
};

type FinancialHealthMetrics = {
  total_revenue: string | number;
  net_revenue: string | number;
  operational_expenses: string | number;
  gross_margin: number;
  ebitda_margin: number;
  cash_on_hand: string | number;
  burn_rate: string | number;
  runway_months: number;
  revenue_trend: TimeSeriesData[];
  expense_trend: TimeSeriesData[];
};

function formatCurrency(value: string | number) {
  const asNumber = typeof value === 'string' ? Number.parseFloat(value) : value;
  if (Number.isNaN(asNumber)) {
    return value;
  }
  return asNumber.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status}`);
  }
  return (await response.json()) as T;
}

export default function PlatformAnalyticsDashboard() {
  const [overview, setOverview] = useState<PlatformOverviewMetrics | null>(null);
  const [revenue, setRevenue] = useState<RevenueAnalytics | null>(null);
  const [growth, setGrowth] = useState<PlatformGrowthMetrics | null>(null);
  const [moderation, setModeration] = useState<ModerationQueueMetrics | null>(null);
  const [performance, setPerformance] = useState<AdminPerformanceMetrics | null>(null);
  const [financials, setFinancials] = useState<FinancialHealthMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [overviewData, revenueData, growthData, moderationData, performanceData, financialData] = await Promise.all([
          fetchJson<PlatformOverviewMetrics>('/api/v1/analytics/platform/overview'),
          fetchJson<RevenueAnalytics>('/api/v1/analytics/platform/revenue'),
          fetchJson<PlatformGrowthMetrics>('/api/v1/analytics/platform/growth'),
          fetchJson<ModerationQueueMetrics>('/api/v1/analytics/admin/moderation'),
          fetchJson<AdminPerformanceMetrics>('/api/v1/analytics/admin/performance'),
          fetchJson<FinancialHealthMetrics>('/api/v1/analytics/admin/financial'),
        ]);
        if (cancelled) {
          return;
        }
        setOverview(overviewData);
        setRevenue(revenueData);
        setGrowth(growthData);
        setModeration(moderationData);
        setPerformance(performanceData);
        setFinancials(financialData);
      } catch (err) {
        console.error('Failed to load analytics dashboard', err);
        if (!cancelled) {
          setError('Unable to load analytics insights. Please try again later.');
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
  }, []);

  if (loading) {
    return <div className="p-6 text-slate-600">Loading analytics…</div>;
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
        <h1 className="text-3xl font-semibold text-slate-900">Platform analytics</h1>
        <p className="text-slate-600">
          Executive overview of bookings, revenue, growth, and moderation performance across Prep.
        </p>
      </header>

      {overview ? (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">Platform overview</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Total users" value={overview.total_users.toLocaleString()} />
            <MetricCard label="Hosts" value={overview.total_hosts.toLocaleString()} />
            <MetricCard label="Active kitchens" value={`${overview.active_kitchens} / ${overview.total_kitchens}`} />
            <MetricCard label="Bookings" value={overview.total_bookings.toLocaleString()} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <TrendCard title="Bookings trend" points={overview.bookings_trend} />
            <TrendCard title="Revenue trend" points={overview.revenue_trend} formatter={formatCurrency} />
          </div>
        </section>
      ) : null}

      {revenue ? (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">Revenue insights</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard label="Total revenue" value={formatCurrency(revenue.total_revenue)} />
            <MetricCard label="Avg booking value" value={formatCurrency(revenue.average_booking_value)} />
            <MetricCard
              label="Top payment method"
              value={
                revenue.payment_methods_breakdown.length > 0
                  ? `${revenue.payment_methods_breakdown[0].method} · ${formatPercent(
                      revenue.payment_methods_breakdown[0].percentage,
                    )}`
                  : '—'
              }
            />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <TrendCard title="Revenue trends" points={revenue.revenue_trends} formatter={formatCurrency} />
            <TrendCard title="Forecast" points={revenue.revenue_forecast} formatter={formatCurrency} />
          </div>
          {revenue.revenue_by_kitchen.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2 font-medium text-slate-600">Kitchen</th>
                    <th className="px-4 py-2 font-medium text-slate-600">Revenue</th>
                    <th className="px-4 py-2 font-medium text-slate-600">Bookings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {revenue.revenue_by_kitchen.slice(0, 5).map((entry) => (
                    <tr key={entry.kitchen_id}>
                      <td className="px-4 py-2 text-slate-900">{entry.kitchen_name}</td>
                      <td className="px-4 py-2 text-slate-600">{formatCurrency(entry.total_revenue)}</td>
                      <td className="px-4 py-2 text-slate-500">{entry.booking_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      {growth ? (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">Growth funnel</h2>
          <div className="grid gap-4 lg:grid-cols-2">
            <TrendCard title="User signups" points={growth.user_signups} />
            <TrendCard title="Host signups" points={growth.host_signups} />
          </div>
          <TrendCard title="Conversion rate" points={growth.conversion_rate} formatter={formatPercent} />
          {growth.acquisition_channels.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2 font-medium text-slate-600">Channel</th>
                    <th className="px-4 py-2 font-medium text-slate-600">Signups</th>
                    <th className="px-4 py-2 font-medium text-slate-600">Conversion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {growth.acquisition_channels.map((channel) => (
                    <tr key={channel.channel}>
                      <td className="px-4 py-2 text-slate-900">{channel.channel}</td>
                      <td className="px-4 py-2 text-slate-600">{channel.signups.toLocaleString()}</td>
                      <td className="px-4 py-2 text-slate-500">{formatPercent(channel.conversion_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      {moderation || performance ? (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">Moderation team</h2>
          {moderation ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="Pending" value={moderation.pending.toString()} />
              <MetricCard label="In review" value={moderation.in_review.toString()} />
              <MetricCard label="Escalated" value={moderation.escalated.toString()} />
              <MetricCard
                label="Avg review time"
                value={`${moderation.average_review_time_hours.toFixed(1)} hrs`}
              />
            </div>
          ) : null}
          {performance ? (
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2 font-medium text-slate-600">Admin</th>
                    <th className="px-4 py-2 font-medium text-slate-600">Resolved</th>
                    <th className="px-4 py-2 font-medium text-slate-600">Resolution time</th>
                    <th className="px-4 py-2 font-medium text-slate-600">Quality</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {performance.team.map((member) => (
                    <tr key={member.admin_id}>
                      <td className="px-4 py-2 text-slate-900">{member.admin_name}</td>
                      <td className="px-4 py-2 text-slate-600">{member.resolved_cases}</td>
                      <td className="px-4 py-2 text-slate-500">{member.average_resolution_time_hours.toFixed(1)} hrs</td>
                      <td className="px-4 py-2 text-slate-500">{formatPercent(member.quality_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      {financials ? (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">Financial health</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Net revenue" value={formatCurrency(financials.net_revenue)} />
            <MetricCard label="Cash" value={formatCurrency(financials.cash_on_hand)} />
            <MetricCard label="Burn" value={formatCurrency(financials.burn_rate)} />
            <MetricCard label="Runway" value={`${financials.runway_months.toFixed(1)} months`} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <TrendCard title="Revenue" points={financials.revenue_trend} formatter={formatCurrency} />
            <TrendCard title="Expenses" points={financials.expense_trend} formatter={formatCurrency} />
          </div>
        </section>
      ) : null}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function TrendCard({
  title,
  points,
  formatter,
}: {
  title: string;
  points: TimeSeriesData[];
  formatter?: (value: number) => string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow">
      <p className="text-sm font-medium text-slate-600">{title}</p>
      {points.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No data available.</p>
      ) : (
        <ul className="mt-3 space-y-2 text-sm text-slate-600">
          {points.slice(-10).map((point) => {
            const value = typeof point.value === 'number' ? point.value : Number(point.value);
            const label = Number.isNaN(value) ? point.value : formatter ? formatter(value) : value.toLocaleString();
            return (
              <li key={`${point.date}-${label}`} className="flex justify-between">
                <span className="text-slate-500">{new Date(point.date).toLocaleDateString()}</span>
                <span className="font-medium text-slate-900">{label}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
