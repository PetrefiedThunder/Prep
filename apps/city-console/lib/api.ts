import { buildAuthHeaders, resolveApiBase } from './config';
import { CityOption, findCityByDiffKey, findCityBySlug } from './cities';

export interface FeeLineItem {
  name: string;
  amount_cents: number;
  kind: string;
  cadence?: string | null;
  unit?: string | null;
  incremental?: boolean;
}

export interface FeeSchedulePayload {
  jurisdiction: string;
  paperwork: string[];
  fees: FeeLineItem[];
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

export interface RequirementResponse {
  id: string;
  requirement_id: string;
  requirement_label: string;
  requirement_type: string;
  jurisdiction_city: string;
  jurisdiction_state: string;
  agency_name: string;
  applies_to: string[];
  required_documents: string[];
  submission_channel: string;
  application_url?: string | null;
  inspection_required: boolean;
  renewal_frequency: string;
  fee_amount?: number | null;
  fee_schedule: string;
  source_url: string;
  last_updated: string;
  rules: Record<string, unknown>;
}

interface DiffVersionSummary {
  version: string;
  released_at: string;
  jurisdictions: string[];
  etag: string;
}

interface DiffVersionDetail {
  version: string;
  released_at: string;
  summary: string;
  jurisdictions: Record<
    string,
    {
      added_requirements?: Array<{ id: string; title: string; severity?: string }>;
      removed_requirements?: Array<{ id: string; title: string }>;
      updated_requirements?: Array<{
        id: string;
        title: string;
        previous?: Record<string, unknown>;
        current?: Record<string, unknown>;
      }>;
      notes?: string;
    }
  >;
}

export interface PolicyDecisionRow {
  version: string;
  releasedAt: string;
  jurisdiction: CityOption;
  summary: string;
  changeCount: number;
  notes?: string;
}

export async function fetchFeeSchedule(citySlug: string): Promise<FeeSchedulePayload> {
  const base = resolveApiBase();
  const city = findCityBySlug(citySlug);
  const headers = { Accept: 'application/json', ...buildAuthHeaders() };
  const response = await fetch(`${base}/city/${city.slug}/fees`, {
    headers,
    next: { revalidate: 300 }
  });

  if (!response.ok) {
    throw new Error(`Failed to load fee schedule for ${city.name}: ${response.status} ${response.statusText}`);
  }

  const payload: FeeSchedulePayload = await response.json();
  return payload;
}

export async function fetchRequirements(citySlug: string): Promise<RequirementResponse[]> {
  const base = resolveApiBase();
  const city = findCityBySlug(citySlug);
  const headers = { Accept: 'application/json', ...buildAuthHeaders() };
  const url = new URL(`${base}/compliance/requirements`);
  url.searchParams.set('jurisdiction', city.requirementJurisdiction);
  const response = await fetch(url, {
    headers,
    cache: 'no-store'
  });

  if (!response.ok) {
    throw new Error(`Failed to load requirements for ${city.name}: ${response.status} ${response.statusText}`);
  }

  const payload: RequirementResponse[] = await response.json();
  return payload;
}

async function fetchDiffVersions(): Promise<DiffVersionSummary[]> {
  const base = resolveApiBase();
  const headers = { Accept: 'application/json', ...buildAuthHeaders() };
  const response = await fetch(`${base}/city/diff/versions`, {
    headers,
    next: { revalidate: 600 }
  });

  if (!response.ok) {
    throw new Error(`Failed to load policy diff versions: ${response.status} ${response.statusText}`);
  }

  const payload = (await response.json()) as { versions?: DiffVersionSummary[] };
  return payload.versions ?? [];
}

async function fetchDiffVersion(version: string): Promise<DiffVersionDetail> {
  const base = resolveApiBase();
  const headers = { Accept: 'application/json', ...buildAuthHeaders() };
  const response = await fetch(`${base}/city/diff/${version}`, {
    headers,
    next: { revalidate: 600 }
  });

  if (!response.ok) {
    throw new Error(`Failed to load policy diff ${version}: ${response.status} ${response.statusText}`);
  }

  const payload: DiffVersionDetail = await response.json();
  return payload;
}

export async function fetchPolicyDecisions(citySlug: string, limit = 5): Promise<PolicyDecisionRow[]> {
  const versions = await fetchDiffVersions();
  if (!versions.length) {
    return [];
  }

  const selectedVersions = versions.slice(0, limit);
  const details = await Promise.all(selectedVersions.map((item) => fetchDiffVersion(item.version)));

  const targetCity = findCityBySlug(citySlug);

  const rows: PolicyDecisionRow[] = [];
  for (const detail of details) {
    for (const [diffKey, payload] of Object.entries(detail.jurisdictions)) {
      const jurisdiction = findCityByDiffKey(diffKey);
      if (!jurisdiction) {
        continue;
      }
      if (jurisdiction.slug !== targetCity.slug) {
        continue;
      }
      const added = payload.added_requirements?.length ?? 0;
      const removed = payload.removed_requirements?.length ?? 0;
      const updated = payload.updated_requirements?.length ?? 0;
      rows.push({
        version: detail.version,
        releasedAt: detail.released_at,
        jurisdiction,
        summary: detail.summary,
        changeCount: added + removed + updated,
        notes: payload.notes
      });
    }
  }

  return rows;
}
