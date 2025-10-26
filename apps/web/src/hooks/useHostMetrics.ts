import { useEffect, useState } from 'react';

/**
 * React hook that retrieves analytics metrics for a specific host.
 *
 * @param hostId - Identifier for the host whose metrics should be fetched.
 * @returns The parsed JSON payload returned from the analytics endpoint or `null` while loading/when unavailable.
 */
export function useHostMetrics<T = unknown>(hostId: string | number | null | undefined) {
  const [metrics, setMetrics] = useState<T | null>(null);

  useEffect(() => {
    if (hostId === null || hostId === undefined || hostId === '') {
      setMetrics(null);
      return;
    }

    const controller = new AbortController();

    const fetchMetrics = async () => {
      try {
        const response = await fetch(`/analytics/host/${hostId}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch host metrics: ${response.status} ${response.statusText}`);
        }

        const payload: T = await response.json();
        if (!controller.signal.aborted) {
          setMetrics(payload);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        console.error('Error fetching host metrics', error);
        setMetrics(null);
      }
    };

    fetchMetrics();

    return () => {
      controller.abort();
    };
  }, [hostId]);

  return metrics;
}
