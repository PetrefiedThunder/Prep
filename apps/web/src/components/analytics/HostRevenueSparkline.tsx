import { useId, useMemo } from 'react';

import { useHostMetrics, type UseHostMetricsResult } from '../../hooks/useHostMetrics';

type RevenueTrendPoint = {
  /** ISO date string representing the day the revenue was recorded. */
  date: string;
  /** Numeric revenue value for the day. */
  value: number;
};

type HostMetricsResponse = {
  host_name?: string;
  revenue_trend?: unknown;
  revenueTrend?: unknown;
  revenue?: { trend?: unknown };
  metrics?: { revenue?: { trend?: unknown } };
  revenue_last_30?: number | string;
  revenueLast30?: number | string;
  total_revenue?: number | string;
  totalRevenue?: number | string;
};

type HostRevenueSparklineProps = {
  /** Identifier of the host whose metrics should be visualised. */
  hostId?: string | number | null;
  /** Number of days represented in the sparkline window. */
  windowDays?: number;
  /** Optional class name applied to the root container. */
  className?: string;
  /** ISO currency code used when displaying aggregate revenue totals. */
  currency?: string;
  /** Locale used for currency formatting. */
  locale?: string;
  /** Custom title displayed in the card header. */
  title?: string;
};

const CHART_WIDTH = 320;
const CHART_HEIGHT = 96;

const formatCurrency = (value: number, currency: string, locale: string) => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
};

const coerceNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const normalizeTrendPoints = (source: unknown): RevenueTrendPoint[] => {
  if (!Array.isArray(source)) {
    return [];
  }

  const points: RevenueTrendPoint[] = [];

  for (let index = 0; index < source.length; index += 1) {
    const entry = source[index];
    if (!entry || typeof entry !== 'object') {
      continue;
    }

    const candidate = entry as Record<string, unknown>;
    const value =
      coerceNumber(candidate.value) ??
      coerceNumber(candidate.revenue) ??
      coerceNumber(candidate.amount);

    if (value == null) {
      continue;
    }

    const rawDate = candidate.period ?? candidate.date ?? candidate.timestamp ?? index;

    let parsedDate: string;
    if (typeof rawDate === 'number') {
      const date = new Date(rawDate);
      parsedDate = Number.isFinite(date.getTime()) ? date.toISOString() : `${index}`;
    } else if (rawDate instanceof Date) {
      parsedDate = rawDate.toISOString();
    } else if (typeof rawDate === 'string') {
      parsedDate = rawDate;
    } else {
      parsedDate = `${index}`;
    }

    points.push({
      date: parsedDate,
      value,
    });
  }

  return points;
};

const buildSparklinePath = (points: RevenueTrendPoint[]) => {
  if (!points.length) {
    return { linePath: '', areaPath: '' };
  }

  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const xStep = points.length > 1 ? CHART_WIDTH / (points.length - 1) : CHART_WIDTH;

  let linePath = '';

  points.forEach((point, index) => {
    const x = index * xStep;
    const normalized = (point.value - min) / range;
    const y = CHART_HEIGHT - normalized * CHART_HEIGHT;
    linePath += `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
  });

  const areaPath = `${linePath} L${CHART_WIDTH},${CHART_HEIGHT} L0,${CHART_HEIGHT} Z`;

  return { linePath, areaPath };
};

const pickTrendPoints = (metrics: HostMetricsResponse | null, windowDays: number) => {
  if (!metrics) {
    return [] as RevenueTrendPoint[];
  }

  const candidateSources = [
    metrics.revenue_trend,
    metrics.revenueTrend,
    metrics.revenue?.trend,
    metrics.metrics?.revenue?.trend,
  ];

  for (const source of candidateSources) {
    const normalized = normalizeTrendPoints(source);
    if (normalized.length) {
      return normalized;
    }
  }

  const totalRevenue =
    coerceNumber(metrics.revenue_last_30) ??
    coerceNumber(metrics.revenueLast30) ??
    coerceNumber(metrics.total_revenue) ??
    coerceNumber(metrics.totalRevenue);

  if (totalRevenue == null) {
    return [];
  }

  const days = Math.max(1, windowDays);
  const dailyValue = totalRevenue / days;
  const today = new Date();
  const fallbackPoints: RevenueTrendPoint[] = [];

  for (let index = days - 1; index >= 0; index -= 1) {
    const current = new Date(today);
    current.setDate(today.getDate() - index);
    fallbackPoints.push({
      date: current.toISOString(),
      value: dailyValue,
    });
  }

  return fallbackPoints;
};

const computeDelta = (points: RevenueTrendPoint[]) => {
  if (points.length < 2) {
    return null;
  }

  const latest = points[points.length - 1]?.value;
  const previous = points[points.length - 2]?.value;

  if (latest == null || previous == null || previous === 0) {
    return null;
  }

  const delta = ((latest - previous) / previous) * 100;
  return Number.isFinite(delta) ? delta : null;
};

export function HostRevenueSparkline({
  hostId = 'current',
  windowDays = 30,
  className,
  currency = 'USD',
  locale = 'en-US',
  title = 'Revenue performance',
}: HostRevenueSparklineProps) {
  const { data, isLoading, error }: UseHostMetricsResult<HostMetricsResponse> = useHostMetrics(hostId);
  const gradientInstanceId = useId();
  const gradientSuffix = useMemo(
    () => gradientInstanceId.replace(/[^a-zA-Z0-9]/g, ''),
    [gradientInstanceId],
  );
  const fillGradientId = `host-sparkline-gradient-${gradientSuffix}`;
  const lineGradientId = `host-sparkline-line-${gradientSuffix}`;

  const trendPoints = useMemo(() => pickTrendPoints(data, windowDays), [data, windowDays]);
  const aggregateRevenue = useMemo(() => {
    if (!trendPoints.length) {
      return (
        coerceNumber(data?.revenue_last_30) ??
        coerceNumber(data?.revenueLast30) ??
        coerceNumber(data?.total_revenue) ??
        coerceNumber(data?.totalRevenue) ??
        0
      );
    }

    return trendPoints.reduce((sum, point) => sum + point.value, 0);
  }, [data, trendPoints]);

  const delta = useMemo(() => computeDelta(trendPoints), [trendPoints]);
  const { linePath, areaPath } = useMemo(() => buildSparklinePath(trendPoints), [trendPoints]);

  const resolvedTitle = data?.host_name ? `${data.host_name} revenue` : title;

  return (
    <section
      className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow ${
        className ?? ''
      }`}
    >
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-slate-600">{resolvedTitle}</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900" data-testid="host-revenue-total">
            {formatCurrency(Math.max(aggregateRevenue, 0), currency, locale)}
          </p>
        </div>
        {delta != null ? (
          <span
            className={`text-sm font-medium ${delta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}
            data-testid="host-revenue-delta"
          >
            {delta >= 0 ? '+' : ''}
            {delta.toFixed(1)}%
          </span>
        ) : null}
      </header>

      <div className="mt-6 h-32">
        {isLoading ? (
          <div
            role="status"
            className="h-full w-full animate-pulse rounded-md bg-slate-200"
            data-testid="host-revenue-sparkline-loading"
          />
        ) : error ? (
          <div
            role="alert"
            className="flex h-full items-center justify-center rounded-md bg-rose-50 p-4 text-sm text-rose-700"
          >
            {error}
          </div>
        ) : trendPoints.length ? (
          <figure className="flex h-full flex-col justify-end" aria-label="Host revenue sparkline">
            <svg
              viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
              preserveAspectRatio="none"
              className="h-full w-full"
              role="img"
              data-testid="host-revenue-sparkline-chart"
            >
              <defs>
                <linearGradient id={fillGradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(37, 99, 235, 0.35)" />
                  <stop offset="100%" stopColor="rgba(37, 99, 235, 0.05)" />
                </linearGradient>
                <linearGradient id={lineGradientId} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#2563eb" />
                  <stop offset="100%" stopColor="#38bdf8" />
                </linearGradient>
              </defs>
              <path d={areaPath} fill={`url(#${fillGradientId})`} />
              <path
                d={linePath}
                fill="none"
                stroke={`url(#${lineGradientId})`}
                strokeWidth={3}
                strokeLinecap="round"
              />
            </svg>
          </figure>
        ) : (
          <div className="flex h-full items-center justify-center rounded-md border border-dashed border-slate-200 text-sm text-slate-500">
            No revenue activity for this period.
          </div>
        )}
      </div>
    </section>
  );
}

export default HostRevenueSparkline;
