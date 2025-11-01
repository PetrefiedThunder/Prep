import Link from 'next/link';

import { CitySelector } from '@/components/controls/city-selector';
import { CsvDownloadButton } from '@/components/controls/csv-download-button';
import { DataSection } from '@/components/layout/data-section';
import { SummaryCard } from '@/components/layout/summary-cards';
import { DataTable } from '@/components/tables/data-table';
import { findCityBySlug } from '@/lib/cities';
import { fetchRequirements } from '@/lib/api';
import { documentsToCsv, mapDocumentsToDisplay } from '@/lib/transformers';

export const metadata = {
  title: 'Documents | Prep City Console'
};

export default async function DocumentsPage({
  searchParams
}: {
  searchParams?: { city?: string };
}) {
  const city = findCityBySlug(searchParams?.city);

  const result = await fetchRequirements(city.slug).then(
    (data) => ({ data }),
    (error) => ({ error })
  );

  const documentRows = result.data ? mapDocumentsToDisplay(result.data) : [];
  const csvRows = documentsToCsv(documentRows, city);

  const agencyCount = new Set(documentRows.map((row) => row.agency)).size;
  const onlineCount = documentRows.filter((row) => (row.link ?? '').startsWith('http')).length;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="section-card">
        <div className="section-header">
          <div>
            <h1 className="section-title">Document readiness</h1>
            <p className="section-description">
              Track official documentation and upload channels required for {city.name}.
            </p>
          </div>
          <CitySelector selected={city} label="Jurisdiction" />
        </div>
        <div className="summary-grid">
          <SummaryCard
            label="Documents tracked"
            value={documentRows.length.toString()}
            helper="Including duplicates across requirements"
          />
          <SummaryCard label="Agencies involved" value={agencyCount.toString()} helper="Unique issuing bodies" />
          <SummaryCard
            label="Online submission"
            value={onlineCount.toString()}
            helper="Documents with direct portal links"
          />
        </div>
      </div>

      <DataSection
        title={`${city.name} document inventory`}
        description="Use exports to share with onboarding and compliance partners."
        controls={<CsvDownloadButton filename={`${city.slug}-documents.csv`} rows={csvRows} />}
      >
        {result.error ? (
          <div className="empty-state">Unable to load requirements: {String(result.error)}</div>
        ) : (
          <DataTable
            columns={[
              { key: 'document', header: 'Document', render: (row: typeof documentRows[number]) => row.document },
              { key: 'requirement', header: 'Requirement', render: (row) => row.requirement },
              { key: 'submission', header: 'Submission channel', render: (row) => row.submissionChannel },
              { key: 'agency', header: 'Agency', render: (row) => row.agency },
              { key: 'lastUpdated', header: 'Last updated', render: (row) => row.lastUpdated },
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
            emptyMessage="No documents configured for this jurisdiction."
          />
        )}
      </DataSection>
    </div>
  );
}
