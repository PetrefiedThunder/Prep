import { useEffect, useState } from 'react';
import type { CityCompliancePayload, FeesResponse, RequirementsResponse, PermitStatus } from '../lib/prepTypes';
import { derivePermitStatus } from '../lib/prepTypes';

export type CityKey = 'san-francisco' | 'joshua-tree';

interface CityComplianceState {
  loading: boolean;
  error?: string;
  data?: CityCompliancePayload;
  status: PermitStatus;
}

const API_BASE = import.meta.env.VITE_PREP_API_BASE_URL ?? '/api';

async function fetchJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function useCityCompliance(city: CityKey): CityComplianceState {
  const [state, setState] = useState<CityComplianceState>({ loading: true, status: 'in_progress' });

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setState({ loading: true, status: 'in_progress' });
      try {
        const [fees, requirements] = (await Promise.all([
          fetchJson<FeesResponse>(`${API_BASE}/city/${city}/fees`, controller.signal),
          fetchJson<RequirementsResponse>(`${API_BASE}/city/${city}/requirements`, controller.signal),
        ])) as [FeesResponse, RequirementsResponse];

        const payload: CityCompliancePayload = { fees, requirements };
        setState({
          loading: false,
          data: payload,
          status: derivePermitStatus(payload.requirements),
        });
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          return;
        }
        setState({
          loading: false,
          error: (error as Error).message,
          status: 'blocked',
        });
      }
    }

    load();

    return () => {
      controller.abort();
    };
  }, [city]);

  return state;
}
