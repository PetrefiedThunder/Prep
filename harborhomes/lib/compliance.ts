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

function resolveComplianceBase() {
  const base = process.env.COMPLIANCE_API_BASE ?? process.env.NEXT_PUBLIC_API_BASE;
  if (!base) {
    throw new Error("COMPLIANCE_API_BASE is not configured");
  }
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

function buildComplianceHeaders(headers?: NextFetchInit["headers"]) {
  const merged = new Headers(headers ?? {});
  if (!merged.has("Accept")) {
    merged.set("Accept", "application/json");
  }
  const apiKey = process.env.COMPLIANCE_API_KEY;
  if (apiKey && !merged.has("x-api-key")) {
    merged.set("x-api-key", apiKey);
  }
  return merged;
}

async function fetchCompliance<T>(path: string, init?: NextFetchInit): Promise<T> {
  const base = resolveComplianceBase();
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;
  const headers = buildComplianceHeaders(init?.headers);
  const requestInit: NextFetchInit = {
    ...init,
    headers,
    next: init?.next ?? { revalidate: DEFAULT_REVALIDATE_SECONDS }
  };

  const response = await fetch(`${base}/${normalizedPath}`, requestInit);

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Failed to load compliance resource at ${normalizedPath}`);
  }

  return (await response.json()) as T;
}

export async function fetchCityCompliance(city: string, init?: NextFetchInit): Promise<CityCompliance> {
  return fetchCompliance<CityCompliance>(`city/${city}/fees`, init);
}

export { resolveComplianceBase, buildComplianceHeaders, fetchCompliance };
