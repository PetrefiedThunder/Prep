import Link from 'next/link';

import { CitySelector } from '@/components/controls/city-selector';
import { CsvDownloadButton } from '@/components/controls/csv-download-button';
import { DataSection } from '@/components/layout/data-section';
import { SummaryCard } from '@/components/layout/summary-cards';
import { DataTable } from '@/components/tables/data-table';
import { findCityBySlug } from '@/lib/cities';
import { fetchPolicyDecisions } from '@/lib/api';
import { mapPolicyDecisionsToDisplay, policyDecisionsToCsv } from '@/lib/transformers';

export const metadata = {
  title: 'Policy decisions | Prep City Console'
};

export default async function PolicyDecisionsPage({
  searchParams
}: {
  searchParams?: { city?: string };
}) {
  const city = findCityBySlug(searchParams?.city);

  const result = await fetchPolicyDecisions(city.slug, 12).then(
    (data) => ({ data }),
    (error) => ({ error })
  );

  const policyRows = result.data ? mapPolicyDecisionsToDisplay(result.data) : [];
  const latestRelease = policyRows[0]?.releasedAt;
  const csvRows = policyDecisionsToCsv(policyRows);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="section-card">
        <div className="section-header">
          <div>
            <h1 className="section-title">Policy decisions</h1>
            <p className="section-description">
              Timeline of policy diffs recorded for {city.name}. Use this feed to brief leadership on regulatory changes.
            </p>
          </div>
          <CitySelector selected={city} label="Jurisdiction" />
        </div>
        <div className="summary-grid">
          <SummaryCard
            label="Change events"
            value={policyRows.reduce((count, row) => count + row.changeCount, 0).toString()}
            helper="Sum of added, removed, and updated requirements"
          />
          <SummaryCard
            label="Published releases"
            value={policyRows.length.toString()}
            helper="Last 12 diff snapshots"
          />
          <SummaryCard
            label="Latest release"
            value={latestRelease ?? 'N/A'}
            helper="Formatted in local timezone"
          />
        </div>
      </div>

      <DataSection
        title={`${city.name} policy decision log`}
        description="Each entry represents a diff published by policy operations."
        controls={<CsvDownloadButton filename={`${city.slug}-policy-decisions.csv`} rows={csvRows} />}
      >
        {result.error ? (
          <div className="empty-state">Unable to load policy decisions: {String(result.error)}</div>
        ) : (
          <DataTable
            columns={[
              { key: 'version', header: 'Version', render: (row: typeof policyRows[number]) => row.version },
              { key: 'releasedAt', header: 'Released', render: (row) => row.releasedAt },
              { key: 'jurisdiction', header: 'Jurisdiction', render: (row) => row.jurisdiction },
              { key: 'summary', header: 'Summary', render: (row) => row.summary },
              { key: 'changeCount', header: 'Change count', render: (row) => row.changeCount },
              {
                key: 'notes',
                header: 'Notes',
                render: (row) => row.notes ?? '—'
              }
            ]}
            data={policyRows}
            emptyMessage="No policy decisions available yet for this jurisdiction."
          />
        )}
        <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--muted-foreground)' }}>
          Looking for related fee changes? Head to the <Link className="link-muted" href="/fees">fee schedule</Link> view.
        </p>
      </DataSection>
    </div>
  );
}
