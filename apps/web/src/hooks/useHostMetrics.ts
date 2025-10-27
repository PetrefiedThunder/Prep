import { useCallback, useEffect, useMemo, useState } from 'react';

export type UseHostMetricsResult<T> = {
  /** Parsed payload returned from the analytics endpoint. */
  data: T | null;
  /** Indicates whether the request is still in-flight. */
  isLoading: boolean;
  /** Error message describing why metrics could not be loaded, if any. */
  error: string | null;
  /** Imperative refetch helper so consumers can manually refresh metrics. */
  refetch: () => Promise<void>;
};

const GENERIC_FETCH_ERROR = 'Unable to load host metrics. Please try again later.';

/**
 * React hook that retrieves analytics metrics for a specific host.
 *
 * @param hostId - Identifier for the host whose metrics should be fetched.
 * @returns Loading state, potential error and parsed JSON payload returned from the analytics endpoint.
 */
export function useHostMetrics<T = unknown>(hostId: string | number | null | undefined): UseHostMetricsResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedHostId = useMemo(() => {
    if (hostId === null || hostId === undefined || hostId === '') {
      return null;
    }

    return String(hostId);
  }, [hostId]);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!normalizedHostId) {
      setData(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/analytics/host/${normalizedHostId}`, {
        signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch host metrics: ${response.status} ${response.statusText}`);
      }

      const payload: T = await response.json();
      setData(payload);
    } catch (err) {
      if (signal?.aborted) {
        return;
      }

      console.error('Error fetching host metrics', err);
      setError(GENERIC_FETCH_ERROR);
      setData(null);
    } finally {
      if (!signal?.aborted) {
        setIsLoading(false);
      }
    }
  }, [normalizedHostId]);

  useEffect(() => {
    const controller = new AbortController();

    void load(controller.signal);

    return () => {
      controller.abort();
    };
  }, [load]);

  const refetch = useCallback(async () => {
    const controller = new AbortController();
    try {
      await load(controller.signal);
    } finally {
      controller.abort();
    }
  }, [load]);

  return { data, isLoading, error, refetch };
}
