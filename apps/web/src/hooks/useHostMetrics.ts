import useSWR, { type SWRConfiguration, type SWRResponse } from 'swr';

type HostIdentifier = string | number | null | undefined;

type UseHostMetricsReturn<T> = Pick<
  SWRResponse<T, Error>,
  'data' | 'error' | 'mutate' | 'isValidating'
> & {
  isLoading: boolean;
};

const fetchHostMetrics = async <T>(url: string): Promise<T> => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch host metrics: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
};

const swrConfig: SWRConfiguration = {
  refreshInterval: 30_000,
};

/**
 * React hook that retrieves analytics metrics for a specific host.
 *
 * @param hostId - Identifier for the host whose metrics should be fetched.
 * @returns SWR response slice with loading state for the requested host metrics.
 */
export function useHostMetrics<T = unknown>(hostId: HostIdentifier): UseHostMetricsReturn<T> {
  const shouldFetch = hostId !== null && hostId !== undefined && `${hostId}`.length > 0;

  const swrResponse = useSWR<T, Error>(
    shouldFetch ? `/analytics/host/${hostId}` : null,
    (url) => fetchHostMetrics<T>(url),
    {
      ...swrConfig,
      refreshInterval: shouldFetch ? swrConfig.refreshInterval : 0,
    },
  );

  return {
    data: swrResponse.data,
    error: swrResponse.error,
    mutate: swrResponse.mutate,
    isValidating: swrResponse.isValidating,
    isLoading: shouldFetch ? swrResponse.isLoading : false,
  };
}
