import { CitySelector } from '@/components/controls/city-selector';
import { CsvDownloadButton } from '@/components/controls/csv-download-button';
import { DataSection } from '@/components/layout/data-section';
import { SummaryCard } from '@/components/layout/summary-cards';
import { DataTable } from '@/components/tables/data-table';
import { findCityBySlug } from '@/lib/cities';
import { fetchFeeSchedule } from '@/lib/api';
import { feesToCsv, mapFeesToDisplay } from '@/lib/transformers';
import { formatCurrencyCents } from '@/lib/formatters';

export const metadata = {
  title: 'Fee schedules | Prep City Console'
};

export default async function FeesPage({
  searchParams
}: {
  searchParams?: { city?: string };
}) {
  const city = findCityBySlug(searchParams?.city);
  const result = await fetchFeeSchedule(city.slug).then(
    (data) => ({ data }),
    (error) => ({ error })
  );

  const feeSchedule = result.data ?? null;
  const feeRows = mapFeesToDisplay(feeSchedule);
  const csvRows = feesToCsv(feeRows, city);

  const totalOneTime = feeSchedule ? formatCurrencyCents(feeSchedule.totals.one_time_cents) : 'N/A';
  const totalRecurring = feeSchedule ? formatCurrencyCents(feeSchedule.totals.recurring_annualized_cents) : 'N/A';
  const incrementalCount = feeSchedule?.totals.incremental_fee_count ?? 0;
  const paperwork = feeSchedule?.paperwork ?? [];

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="section-card">
        <div className="section-header">
          <div>
            <h1 className="section-title">Fee schedules</h1>
            <p className="section-description">
              Definitive line items and paperwork requirements for {city.name} as published by Prep policy.
            </p>
          </div>
          <CitySelector selected={city} label="Jurisdiction" />
        </div>
        <div className="summary-grid">
          <SummaryCard label="One-time fees" value={totalOneTime} helper="Application and onboarding" />
          <SummaryCard label="Annual recurring" value={totalRecurring} helper="12-month run rate" />
          <SummaryCard
            label="Incremental fees"
            value={incrementalCount.toString()}
            helper="Per inspection or usage-based charges"
          />
          <SummaryCard
            label="Paperwork packets"
            value={paperwork.length.toString()}
            helper="Documents bundled with fee submissions"
          />
        </div>
      </div>

      <DataSection
        title={`${city.name} fee line items`}
        description="Line items pulled directly from the compliance gateway."
        controls={<CsvDownloadButton filename={`${city.slug}-fees.csv`} rows={csvRows} />}
      >
        {result.error ? (
          <div className="empty-state">Unable to load fee schedule: {String(result.error)}</div>
        ) : (
          <DataTable
            columns={[
              { key: 'name', header: 'Fee name', render: (row: typeof feeRows[number]) => row.name },
              { key: 'amount', header: 'Amount', render: (row) => row.amount },
              { key: 'cadence', header: 'Cadence', render: (row) => row.cadence },
              { key: 'kind', header: 'Type', render: (row) => row.kind },
              { key: 'unit', header: 'Unit / trigger', render: (row) => row.unit }
            ]}
            data={feeRows}
            emptyMessage="Fee schedule not yet published for this jurisdiction."
          />
        )}
      </DataSection>

      <DataSection
        title="Supporting paperwork"
        description="Document templates or forms that accompany the above fees."
      >
        {paperwork.length === 0 ? (
          <div className="empty-state">No supporting paperwork listed for this jurisdiction.</div>
        ) : (
          <ul style={{ listStyle: 'disc', paddingLeft: '1.5rem', margin: 0, color: 'var(--muted-foreground)' }}>
            {paperwork.map((item) => (
              <li key={item} style={{ marginBottom: '0.5rem' }}>
                {item}
              </li>
            ))}
          </ul>
        )}
      </DataSection>
    </div>
  );
}
