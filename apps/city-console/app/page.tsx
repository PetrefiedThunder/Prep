import React from "react";
const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8080";
async function get(city: string, path: string) {
  const r = await fetch(`${API}/city/${encodeURIComponent(city)}/${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} ${city} ${r.status}`);
  return r.json();
}
export default async function Page() {
  const cities = ["sf","joshua tree"];
  const data = await Promise.all(cities.map(async c => ({
    city: c,
    fees: await get(c,"fees"),
    reqs: await get(c,"requirements"),
  })));
  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <h1 className="text-2xl font-bold">City Console — Read-only</h1>
        {data.map(({city,fees,reqs}) => (
          <div key={city} className="rounded-2xl border bg-white p-4 space-y-3">
            <h2 className="text-xl font-semibold">{city.toUpperCase()}</h2>
            <div className="grid md:grid-cols-3 gap-3">
              <div className="rounded-xl border p-3">
                <div className="text-xs uppercase text-slate-500">Blocking requirements</div>
                <div className="text-xl font-bold">{reqs.validation?.blocking_count ?? 0}</div>
              </div>
              <div className="rounded-xl border p-3">
                <div className="text-xs uppercase text-slate-500">One-time fees</div>
                <div className="text-xl font-bold">{(fees.totals?.one_time_cents ?? 0)/100}</div>
              </div>
              <div className="rounded-xl border p-3">
                <div className="text-xs uppercase text-slate-500">Recurring annualized</div>
                <div className="text-xl font-bold">{(fees.totals?.recurring_annualized_cents ?? 0)/100}</div>
              </div>
            </div>
            <div className="text-sm text-slate-600">Requirements: {reqs.requirements?.length ?? 0} • Fees: {fees.fees?.length ?? 0}</div>
          </div>
        ))}
      </div>
import Link from 'next/link';

import { CitySelector } from '@/components/controls/city-selector';
import { CsvDownloadButton } from '@/components/controls/csv-download-button';
import { DataSection } from '@/components/layout/data-section';
import { SummaryCard } from '@/components/layout/summary-cards';
import { DataTable } from '@/components/tables/data-table';
import { findCityBySlug } from '@/lib/cities';
import { fetchFeeSchedule, fetchPolicyDecisions, fetchRequirements } from '@/lib/api';
import {
  documentsToCsv,
  feesToCsv,
  mapDocumentsToDisplay,
  mapFeesToDisplay,
  mapPolicyDecisionsToDisplay,
  policyDecisionsToCsv
} from '@/lib/transformers';
import { formatCurrencyCents } from '@/lib/formatters';

export default async function OverviewPage({
  searchParams
}: {
  searchParams?: { city?: string };
}) {
  const city = findCityBySlug(searchParams?.city);

  const [feeResult, policyResult, requirementResult] = await Promise.allSettled([
    fetchFeeSchedule(city.slug),
    fetchPolicyDecisions(city.slug, 3),
    fetchRequirements(city.slug)
  ]);

  const feeSchedule = feeResult.status === 'fulfilled' ? feeResult.value : null;
  const feeError = feeResult.status === 'rejected' ? feeResult.reason : null;
  const policies = policyResult.status === 'fulfilled' ? policyResult.value : [];
  const policyError = policyResult.status === 'rejected' ? policyResult.reason : null;
  const requirements = requirementResult.status === 'fulfilled' ? requirementResult.value : [];
  const requirementError = requirementResult.status === 'rejected' ? requirementResult.reason : null;

  const feeRows = mapFeesToDisplay(feeSchedule);
  const policyRows = mapPolicyDecisionsToDisplay(policies);
  const documentRows = mapDocumentsToDisplay(requirements).slice(0, 5);

  const oneTimeFees = feeSchedule?.totals.one_time_cents ?? 0;
  const recurringFees = feeSchedule?.totals.recurring_annualized_cents ?? 0;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      <div className="section-card">
        <div className="section-header">
          <div>
            <h1 className="section-title">City overview</h1>
            <p className="section-description">
              Monitor policy and compliance signals for the selected jurisdiction.
            </p>
          </div>
          <CitySelector selected={city} label="Jurisdiction" />
        </div>
        <div className="summary-grid">
          <SummaryCard
            label="One-time fees"
            value={formatCurrencyCents(oneTimeFees)}
            helper="Latest published schedule"
          />
          <SummaryCard
            label="Annualized recurring fees"
            value={formatCurrencyCents(recurringFees)}
            helper="12 month run-rate"
          />
          <SummaryCard
            label="Open policy updates"
            value={policyRows.length.toString()}
            helper={policyError ? 'Unable to refresh policy feed' : 'Past 3 published diffs'}
          />
          <SummaryCard
            label="Required documents"
            value={documentRows.length.toString()}
            helper={requirementError ? 'Requirements unavailable' : 'Documents flagged for collection'}
          />
        </div>
      </div>

      <DataSection
        title="Recent policy decisions"
        description="Latest compliance diffs applied to this jurisdiction."
        controls={
          <CsvDownloadButton
            filename={`${city.slug}-policy-decisions.csv`}
            rows={policyDecisionsToCsv(policyRows)}
          />
        }
      >
        {policyError ? (
          <div className="empty-state">Unable to load policy decisions: {String(policyError)}</div>
        ) : (
          <DataTable
            columns={[
              { key: 'version', header: 'Version', render: (row: typeof policyRows[number]) => row.version },
              { key: 'releasedAt', header: 'Released', render: (row) => row.releasedAt },
              { key: 'summary', header: 'Summary', render: (row) => row.summary },
              { key: 'changeCount', header: 'Changes', render: (row) => row.changeCount },
              {
                key: 'notes',
                header: 'Notes',
                render: (row) => row.notes ?? '—'
              }
            ]}
            data={policyRows}
            emptyMessage="No policy decisions captured for this jurisdiction yet."
          />
        )}
        <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--muted-foreground)' }}>
          Need the full timeline? View the detailed <Link className="link-muted" href="/policy-decisions">policy decisions feed</Link>.
        </p>
      </DataSection>

      <DataSection
        title="Fee schedule overview"
        description="Most recent fee line items published to the gateway."
        controls={
          <CsvDownloadButton
            filename={`${city.slug}-fees.csv`}
            rows={feesToCsv(feeRows, city)}
          />
        }
      >
        {feeError ? (
          <div className="empty-state">Unable to load fee schedule: {String(feeError)}</div>
        ) : (
          <DataTable
            columns={[
              { key: 'name', header: 'Fee name', render: (row: typeof feeRows[number]) => row.name },
              { key: 'amount', header: 'Amount', render: (row) => row.amount },
              { key: 'cadence', header: 'Cadence', render: (row) => row.cadence },
              { key: 'kind', header: 'Type', render: (row) => row.kind },
              { key: 'unit', header: 'Unit', render: (row) => row.unit }
            ]}
            data={feeRows.slice(0, 5)}
            emptyMessage="No fee entries available for this jurisdiction."
          />
        )}
        <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--muted-foreground)' }}>
          See the <Link className="link-muted" href="/fees">full fee schedule</Link> for totals and validation context.
        </p>
      </DataSection>

      <DataSection
        title="Key document links"
        description="Documents and submission channels required for compliance upkeep."
        controls={
          <CsvDownloadButton
            filename={`${city.slug}-documents.csv`}
            rows={documentsToCsv(documentRows, city)}
          />
        }
      >
        {requirementError ? (
          <div className="empty-state">Unable to load document requirements: {String(requirementError)}</div>
        ) : (
          <DataTable
            columns={[
              { key: 'document', header: 'Document', render: (row: typeof documentRows[number]) => row.document },
              { key: 'requirement', header: 'Requirement', render: (row) => row.requirement },
              { key: 'submission', header: 'Submission channel', render: (row) => row.submissionChannel },
              { key: 'agency', header: 'Agency', render: (row) => row.agency },
              {
                key: 'link',
                header: 'Link',
                render: (row) =>
                  row.link ? (
                    <Link className="link-muted" href={row.link} target="_blank" rel="noreferrer">
                      Open
                    </Link>
                  ) : (
                    '—'
                  )
              }
            ]}
            data={documentRows}
            emptyMessage="No document references published for this jurisdiction."
          />
        )}
        <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--muted-foreground)' }}>
          Dive deeper on the <Link className="link-muted" href="/documents">documents view</Link> for filtering and exports.
        </p>
      </DataSection>
    </div>
  );
}
