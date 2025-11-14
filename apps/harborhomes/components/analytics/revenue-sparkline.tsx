import { useId, useMemo } from 'react';
import { format, isValid, parseISO } from 'date-fns';
import type { TooltipProps } from 'recharts';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import type { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCurrency } from '@/lib/currency';
import { cn } from '@/lib/utils';
import { useHostMetrics, type HostMetric } from '@/hooks/use-host-metrics';

type RevenueSparklineProps = {
  hostId?: string;
  days?: number;
  currency?: string;
  locale?: string;
  className?: string;
};

type SparklineTooltipProps = TooltipProps<ValueType, NameType> & {
  currency: string;
  locale: string;
};

const SparklineTooltip = ({ active, payload, label, currency, locale }: SparklineTooltipProps) => {
  if (!active || !payload?.length) {
    return null;
  }

  const value = payload[0]?.value;
  if (typeof value !== 'number') {
    return null;
  }

  const parsedLabel = typeof label === 'string' ? parseISO(label) : null;
  const formattedLabel = parsedLabel && isValid(parsedLabel) ? format(parsedLabel, 'PP') : label;

  return (
    <div className="rounded-md border border-border bg-background px-3 py-2 text-xs shadow-sm">
      <div className="font-medium text-ink">{formattedLabel}</div>
      <div className="text-muted-ink">{formatCurrency(value, currency, locale)}</div>
    </div>
  );
};

const getSeries = (metrics: HostMetric[], days: number) => {
  if (!metrics.length) return [] as HostMetric[];
  if (metrics.length <= days) return metrics;
  return metrics.slice(metrics.length - days);
};

const percentDelta = (latest: number | null, previous: number | null) => {
  if (latest == null || previous == null || previous === 0) {
    return null;
  }

  const delta = ((latest - previous) / previous) * 100;
  if (!Number.isFinite(delta)) {
    return null;
  }

  return delta;
};

export const RevenueSparkline = ({
  hostId,
  days = 30,
  currency = 'USD',
  locale = 'en-US',
  className,
}: RevenueSparklineProps) => {
  const { metrics, isLoading, error, isFallback, refreshedAt } = useHostMetrics({ hostId, windowDays: days });
  const gradientInstanceId = useId();
  const gradientId = useMemo(
    () => `revenueSparklineGradient-${gradientInstanceId.replace(/[^a-zA-Z0-9]/g, '')}`,
    [gradientInstanceId],
  );

  const series = useMemo(() => getSeries(metrics, days), [metrics, days]);
  const totalRevenue = useMemo(() => series.reduce((sum, point) => sum + point.revenue, 0), [series]);
  const latestRevenue = series.at(-1)?.revenue ?? null;
  const previousRevenue = series.length > 1 ? series[series.length - 2]?.revenue ?? null : null;
  const delta = useMemo(() => percentDelta(latestRevenue, previousRevenue), [latestRevenue, previousRevenue]);

  const statusMessage = isFallback
    ? 'Showing simulated performance due to live data being unavailable.'
    : refreshedAt
      ? `Updated ${format(refreshedAt, 'PPpp')}`
      : 'Awaiting latest metrics.';

  return (
    <Card className={cn('relative overflow-hidden', className)}>
      <CardHeader className="space-y-2 pb-0">
        <CardTitle className="text-sm font-medium text-muted-ink">Revenue (last {days} days)</CardTitle>
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-2xl font-semibold text-ink">
            {formatCurrency(totalRevenue, currency, locale)}
          </span>
          {delta != null ? (
            <span className={cn('text-xs font-medium', delta >= 0 ? 'text-emerald-600' : 'text-rose-600')}>
              {delta >= 0 ? '+' : ''}
              {delta.toFixed(1)}% vs prev day
            </span>
          ) : null}
        </div>
        <p className="text-xs text-muted-ink">{statusMessage}</p>
        {error && !isFallback ? (
          <p className="text-xs text-rose-600" role="status">
            {error}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="mt-4 h-36">
        {isLoading ? (
          <Skeleton data-testid="revenue-sparkline-skeleton" className="h-full w-full" />
        ) : series.length ? (
          <div data-testid="revenue-sparkline-chart" className="h-full w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" hide />
                <Tooltip
                  cursor={{ stroke: 'rgba(14, 165, 233, 0.25)', strokeWidth: 2 }}
                  content={(props) => <SparklineTooltip {...props} currency={currency} locale={locale} />}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                  fill={`url(#${gradientId})`}
                  activeDot={{ r: 3 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-ink">
            No revenue data for this period.
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RevenueSparkline;
