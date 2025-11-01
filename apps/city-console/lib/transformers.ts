import type { PolicyDecisionRow, FeeSchedulePayload, RequirementResponse } from './api';
import { formatCurrencyCents, formatDate, formatFrequency } from './formatters';
import { CityOption } from './cities';

export interface PolicyDecisionDisplayRow {
  version: string;
  releasedAt: string;
  jurisdiction: string;
  summary: string;
  changeCount: number;
  notes?: string;
}

export function mapPolicyDecisionsToDisplay(rows: PolicyDecisionRow[]): PolicyDecisionDisplayRow[] {
  return rows.map((row) => ({
    version: row.version,
    releasedAt: formatDate(row.releasedAt),
    jurisdiction: row.jurisdiction.name,
    summary: row.summary,
    changeCount: row.changeCount,
    notes: row.notes
  }));
}

export function policyDecisionsToCsv(rows: PolicyDecisionDisplayRow[]): Array<Record<string, string | number | null>> {
  return rows.map((row) => ({
    version: row.version,
    released_at: row.releasedAt,
    jurisdiction: row.jurisdiction,
    change_count: row.changeCount,
    summary: row.summary,
    notes: row.notes ?? ''
  }));
}

export interface FeeDisplayRow {
  name: string;
  cadence: string;
  amount: string;
  kind: string;
  unit: string;
}

export function mapFeesToDisplay(schedule: FeeSchedulePayload | null | undefined): FeeDisplayRow[] {
  if (!schedule) {
    return [];
  }
  return schedule.fees.map((fee) => ({
    name: fee.name,
    cadence: formatFrequency(fee.cadence),
    amount: formatCurrencyCents(fee.amount_cents ?? 0),
    kind: fee.kind.replace(/_/g, ' '),
    unit: fee.unit ? fee.unit.replace(/_/g, ' ') : fee.incremental ? 'Incremental' : 'Per filing'
  }));
}

export function feesToCsv(rows: FeeDisplayRow[], city: CityOption): Array<Record<string, string | number | null>> {
  return rows.map((row) => ({
    city: city.name,
    fee_name: row.name,
    cadence: row.cadence,
    amount: row.amount,
    kind: row.kind,
    unit: row.unit
  }));
}

export interface DocumentDisplayRow {
  requirement: string;
  document: string;
  submissionChannel: string;
  agency: string;
  lastUpdated: string;
  link?: string;
}

export function mapDocumentsToDisplay(requirements: RequirementResponse[] | null | undefined): DocumentDisplayRow[] {
  if (!requirements?.length) {
    return [];
  }

  const rows: DocumentDisplayRow[] = [];
  for (const requirement of requirements) {
    const documents = requirement.required_documents.length ? requirement.required_documents : ['Supporting documentation'];
    for (const document of documents) {
      rows.push({
        requirement: requirement.requirement_label,
        document,
        submissionChannel: requirement.submission_channel,
        agency: requirement.agency_name,
        lastUpdated: formatDate(requirement.last_updated),
        link: requirement.application_url ?? requirement.source_url
      });
    }
  }
  return rows;
}

export function documentsToCsv(rows: DocumentDisplayRow[], city: CityOption): Array<Record<string, string | number | null>> {
  return rows.map((row) => ({
    city: city.name,
    requirement: row.requirement,
    document: row.document,
    submission_channel: row.submissionChannel,
    agency: row.agency,
    last_updated: row.lastUpdated,
    link: row.link ?? ''
  }));
}
