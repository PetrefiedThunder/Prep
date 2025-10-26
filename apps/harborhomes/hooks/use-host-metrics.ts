import { useEffect, useState } from 'react';
import { addDays, formatISO, isValid, parseISO, startOfDay, subDays } from 'date-fns';

type NullableDate = Date | null;

export type HostMetricPoint = {
  date: string;
  revenue: number;
  bookings: number;
  occupancy: number;
};

export type UseHostMetricsOptions = {
  /**
   * Explicit host identifier. When omitted the current authenticated host is assumed.
   */
  hostId?: string;
  /**
   * Number of trailing days to request. Defaults to 30 days.
   */
  windowDays?: number;
  /**
   * Allows consumers to opt-out of automatic fetching (useful for SSR or conditional views).
   */
  enabled?: boolean;
};

type HostMetricsResponse = {
  metrics?: Array<Partial<HostMetricPoint> & { date?: string | Date }>;
  refreshedAt?: string;
};

export type UseHostMetricsResult = {
  metrics: HostMetricPoint[];
  isLoading: boolean;
  error: string | null;
  isFallback: boolean;
  refreshedAt: NullableDate;
};

const HOST_METRICS_FALLBACK_MESSAGE = 'Live metrics unavailable. Displaying simulated performance.';

const safeIsoDate = (input: unknown): string | null => {
  if (input instanceof Date && isValid(input)) {
    return formatISO(startOfDay(input), { representation: 'date' });
  }

  if (typeof input === 'string') {
    const parsed = parseISO(input);
    if (isValid(parsed)) {
      return formatISO(startOfDay(parsed), { representation: 'date' });
    }

    const fallback = new Date(input);
    if (!Number.isNaN(fallback.getTime())) {
      return formatISO(startOfDay(fallback), { representation: 'date' });
    }
  }

  return null;
};

const sanitizeMetric = (metric: unknown): HostMetricPoint | null => {
  if (!metric || typeof metric !== 'object') return null;
  const candidate = metric as Partial<HostMetricPoint> & { date?: string | Date };
  const isoDate = safeIsoDate(candidate.date);
  if (!isoDate) return null;

  const revenue = toPositiveNumber(candidate.revenue);
  const bookings = toPositiveNumber(candidate.bookings);
  const occupancy = clamp(toPositiveNumber(candidate.occupancy), 0, 100);

  return {
    date: isoDate,
    revenue,
    bookings,
    occupancy,
  };
};

const toPositiveNumber = (value: unknown): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(0, value);
  }

  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) {
    return 0;
  }

  return Math.max(0, numeric);
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const fillMissingDays = (data: HostMetricPoint[], windowDays: number): HostMetricPoint[] => {
  const windowSize = Math.max(1, windowDays);
  const today = startOfDay(new Date());
  const startDate = subDays(today, windowSize - 1);
  const map = new Map(data.map((point) => [point.date, point]));
  const filled: HostMetricPoint[] = [];

  for (let index = 0; index < windowSize; index += 1) {
    const current = addDays(startDate, index);
    const key = formatISO(current, { representation: 'date' });
    const existing = map.get(key);
    filled.push(
      existing ?? {
        date: key,
        revenue: 0,
        bookings: 0,
        occupancy: 0,
      },
    );
  }

  return filled;
};

const normalizeMetrics = (
  metrics: Array<Partial<HostMetricPoint> & { date?: string | Date }> | undefined,
  windowDays: number,
): HostMetricPoint[] => {
  if (!metrics?.length) {
    return fillMissingDays([], windowDays);
  }

  const sanitized = metrics
    .map((metric) => sanitizeMetric(metric))
    .filter((metric): metric is HostMetricPoint => metric !== null);

  if (!sanitized.length) {
    return fillMissingDays([], windowDays);
  }

  sanitized.sort((a, b) => a.date.localeCompare(b.date));

  const windowSize = Math.max(1, windowDays);
  const today = startOfDay(new Date());
  const startDate = subDays(today, windowSize - 1);
  const earliestKey = formatISO(startDate, { representation: 'date' });
  const latestKey = formatISO(today, { representation: 'date' });

  const bounded = sanitized.filter((metric) => metric.date >= earliestKey && metric.date <= latestKey);

  return fillMissingDays(bounded, windowDays);
};

const buildFallbackMetrics = (windowDays: number): HostMetricPoint[] => {
  const windowSize = Math.max(1, windowDays);
  const today = startOfDay(new Date());
  const startDate = subDays(today, windowSize - 1);
  const points: HostMetricPoint[] = [];

  for (let index = 0; index < windowSize; index += 1) {
    const current = addDays(startDate, index);
    const weekendBoost = current.getDay() === 5 || current.getDay() === 6 ? 420 : 0;
    const seasonalSwing = Math.sin(index / 4.1) * 260;
    const growthTrend = index * 24;
    const revenue = Math.max(180, Math.round(3600 + seasonalSwing + weekendBoost + growthTrend));

    points.push({
      date: formatISO(current, { representation: 'date' }),
      revenue,
      bookings: Math.max(1, Math.round(revenue / 275)),
      occupancy: clamp(Math.round(66 + Math.sin(index / 3.2) * 14 + weekendBoost / 40), 0, 100),
    });
  }

  return points;
};

const resolveEndpoint = (hostId: string, windowDays: number) => {
  if (!hostId || hostId === 'current' || hostId === 'me') {
    return `/api/v1/hosts/me/metrics?windowDays=${windowDays}`;
  }

  return `/api/v1/hosts/${encodeURIComponent(hostId)}/metrics?windowDays=${windowDays}`;
};

export const useHostMetrics = (options: UseHostMetricsOptions = {}): UseHostMetricsResult => {
  const { hostId = 'current', windowDays = 30, enabled = true } = options;
  const [metrics, setMetrics] = useState<HostMetricPoint[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);
  const [isFallback, setIsFallback] = useState(false);
  const [refreshedAt, setRefreshedAt] = useState<NullableDate>(null);

  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      setMetrics([]);
      setError(null);
      setIsFallback(false);
      setRefreshedAt(null);
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    const load = async () => {
      setIsLoading(true);
      setError(null);
      setIsFallback(false);

      try {
        const response = await fetch(resolveEndpoint(hostId, windowDays), {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to load host metrics (status ${response.status})`);
        }

        const payload = (await response.json()) as HostMetricsResponse;
        if (cancelled) return;

        const normalized = normalizeMetrics(payload.metrics, windowDays);
        setMetrics(normalized);
        setRefreshedAt(payload.refreshedAt ? new Date(payload.refreshedAt) : new Date());
      } catch (err) {
        if (cancelled) return;

        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }

        setMetrics(buildFallbackMetrics(windowDays));
        setIsFallback(true);
        setRefreshedAt(new Date());
        setError(HOST_METRICS_FALLBACK_MESSAGE);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [enabled, hostId, windowDays]);

  return {
    metrics,
    isLoading,
    error,
    isFallback,
    refreshedAt,
  };
};

export type { HostMetricPoint as HostMetric };
