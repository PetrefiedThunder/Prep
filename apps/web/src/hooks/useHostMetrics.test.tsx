import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('swr', () => {
  const React = require('react');
  const { useCallback, useEffect, useMemo, useRef, useState } = React;

  type Key = string | null;
  type Fetcher<T> = (key: string) => Promise<T>;
  type Config = { refreshInterval?: number } | undefined;

  const useSWR = <T, E = Error>(key: Key, fetcher: Fetcher<T>, config: Config = {}) => {
    const [data, setData] = useState<T | undefined>(undefined);
    const [error, setError] = useState<E | undefined>(undefined);
    const [isLoading, setIsLoading] = useState<boolean>(Boolean(key));
    const [isValidating, setIsValidating] = useState<boolean>(false);
    const refreshInterval = config?.refreshInterval ?? 0;
    const isMountedRef = useRef(true);

    const executeFetch = useCallback(async () => {
      if (!key) {
        return;
      }
      setIsValidating(true);
      setIsLoading(true);
      try {
        const result = await fetcher(key);
        if (isMountedRef.current) {
          setData(result);
          setError(undefined);
        }
      } catch (err) {
        if (isMountedRef.current) {
          setError(err as E);
        }
      } finally {
        if (isMountedRef.current) {
          setIsValidating(false);
          setIsLoading(false);
        }
      }
    }, [fetcher, key]);

    useEffect(() => {
      isMountedRef.current = true;
      if (key) {
        void executeFetch();
      } else {
        setData(undefined);
        setError(undefined);
        setIsLoading(false);
      }
      return () => {
        isMountedRef.current = false;
      };
    }, [executeFetch, key]);

    useEffect(() => {
      if (!key || !refreshInterval) {
        return undefined;
      }
      const id = setInterval(() => {
        void executeFetch();
      }, refreshInterval);
      return () => clearInterval(id);
    }, [executeFetch, key, refreshInterval]);

    const mutate = useCallback(
      async (value: T | ((current: T | undefined) => T)) => {
        const newValue = value instanceof Function ? value(data) : value;
        setData(newValue);
        return newValue;
      },
      [data],
    );

    return useMemo(
      () => ({
        data,
        error,
        isLoading,
        isValidating,
        mutate,
      }),
      [data, error, isLoading, isValidating, mutate],
    );
  };

  return {
    __esModule: true,
    default: useSWR,
  };
});

import { useHostMetrics } from './useHostMetrics';

type FetchMock = ReturnType<typeof vi.fn>;

describe('useHostMetrics', () => {
  let fetchMock: FetchMock;

  beforeEach(() => {
    vi.useFakeTimers();
    fetchMock = vi.fn();
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('returns loading state while fetching metrics', () => {
    fetchMock.mockResolvedValue(
      Promise.resolve({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: () => Promise.resolve({}),
      }),
    );

    const { result } = renderHook(() => useHostMetrics('host-1'));

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('returns metrics once fetched', async () => {
    const metrics = { value: 42 };
    fetchMock.mockResolvedValue(
      Promise.resolve({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: () => Promise.resolve(metrics),
      }),
    );

    const { result } = renderHook(() => useHostMetrics<typeof metrics>('host-2'));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data).toEqual(metrics);
    expect(result.current.error).toBeUndefined();
  });

  it('exposes errors encountered while fetching', async () => {
    fetchMock.mockResolvedValue(
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        json: () => Promise.resolve({}),
      }),
    );

    const { result } = renderHook(() => useHostMetrics('host-3'));

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.data).toBeUndefined();
  });

  it('revalidates every 30 seconds when a host id is provided', async () => {
    const initialMetrics = { value: 1 };
    const updatedMetrics = { value: 2 };

    fetchMock
      .mockResolvedValueOnce(
        Promise.resolve({
          ok: true,
          status: 200,
          statusText: 'OK',
          json: () => Promise.resolve(initialMetrics),
        }),
      )
      .mockResolvedValueOnce(
        Promise.resolve({
          ok: true,
          status: 200,
          statusText: 'OK',
          json: () => Promise.resolve(updatedMetrics),
        }),
      );

    const { result } = renderHook(() => useHostMetrics('host-4'));

    await waitFor(() => expect(result.current.data).toEqual(initialMetrics));

    await act(async () => {
      vi.advanceTimersByTime(30_000);
      await Promise.resolve();
    });

    await waitFor(() => expect(result.current.data).toEqual(updatedMetrics));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
