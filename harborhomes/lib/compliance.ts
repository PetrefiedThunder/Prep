export type FeeKind = "one_time" | "recurring" | "incremental";

export interface Fee {
  name: string;
  amount_cents: number;
  kind: FeeKind;
  cadence?: string;
  unit?: string;
}

export interface CityCompliance {
  jurisdiction: string;
  paperwork: string[];
  fees: Fee[];
  totals: {
    one_time_cents: number;
    recurring_annualized_cents: number;
    incremental_fee_count: number;
  };
  validation: {
    is_valid: boolean;
    issues: string[];
  };
}

type NextFetchInit = RequestInit & { next?: { revalidate?: number } };

const DEFAULT_REVALIDATE_SECONDS = 60 * 60; // 1 hour

export async function fetchCityCompliance(city: string, init?: NextFetchInit): Promise<CityCompliance> {
  const base = process.env.NEXT_PUBLIC_API_BASE;
  if (!base) {
    throw new Error("NEXT_PUBLIC_API_BASE is not configured");
  }

  const normalizedBase = base.endsWith("/") ? base.slice(0, -1) : base;
  const headers = { Accept: "application/json", ...(init?.headers ?? {}) };
  const requestInit: NextFetchInit = {
    ...init,
    headers,
    next: init?.next ?? { revalidate: DEFAULT_REVALIDATE_SECONDS }
  };

  const response = await fetch(`${normalizedBase}/city/${city}/fees`, requestInit);

  if (!response.ok) {
    throw new Error(`Failed to load compliance data for ${city}`);
  }

  const payload: CityCompliance = await response.json();
  return payload;
}
