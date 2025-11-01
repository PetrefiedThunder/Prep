export type FeeKind = 'one_time' | 'recurring' | 'incremental';

export interface FeeItem {
  id: string;
  label: string;
  amount: number;
  currency: string;
  kind: FeeKind;
  cadence?: string;
  unit?: string;
  description?: string;
}

export interface FeeTotals {
  one_time?: number;
  recurring?: number;
  incremental?: number;
}

export interface FeesResponse {
  city: string;
  currency: string;
  totals: FeeTotals;
  items: FeeItem[];
  last_validated_at?: string;
  validation_issues?: string[];
}

export type RequirementStatus = 'met' | 'outstanding' | 'blocked';

export interface RequirementItem {
  id: string;
  title: string;
  status: RequirementStatus;
  party: string;
  blocking?: boolean;
  due_date?: string;
  description?: string;
  documentation_url?: string;
}

export interface RequirementsParty {
  party: string;
  label: string;
  requirements: RequirementItem[];
}

export interface ChangeCandidate {
  id: string;
  title: string;
  summary: string;
}

export interface RequirementsResponse {
  city: string;
  blocking_count: number;
  counts_by_party: Record<string, number>;
  parties: RequirementsParty[];
  change_candidates?: ChangeCandidate[];
  last_updated_at?: string;
}

export interface CityCompliancePayload {
  fees: FeesResponse;
  requirements: RequirementsResponse;
}

export type PermitStatus = 'ready' | 'in_progress' | 'blocked';

export function derivePermitStatus(bundle?: RequirementsResponse): PermitStatus {
  if (!bundle) {
    return 'in_progress';
  }

  if (bundle.blocking_count === 0) {
    return 'ready';
  }

  return 'in_progress';
}

export function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}

export function friendlyFeeKind(kind: FeeKind): string {
  switch (kind) {
    case 'one_time':
      return 'One-time';
    case 'recurring':
      return 'Recurring';
    case 'incremental':
      return 'Incremental';
    default:
      return kind;
  }
}

export function friendlyRequirementStatus(status: RequirementStatus): string {
  switch (status) {
    case 'met':
      return 'Met';
    case 'blocked':
      return 'Blocked';
    case 'outstanding':
    default:
      return 'Outstanding';
  }
}
