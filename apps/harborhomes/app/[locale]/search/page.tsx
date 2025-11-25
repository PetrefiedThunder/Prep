import { getListings } from '@/lib/api-client';
import { ResultsLayout } from '@/components/search/results-layout';
import { FiltersDialog } from '@/components/search/filters-dialog';

export default async function SearchPage() {
  const listings = await getListings();
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Stays in HarborHomes network</h1>
          <p className="text-sm text-muted-ink">{listings.length} curated homes</p>
        </div>
        <div className="flex gap-3">
          <button className="rounded-full border border-border px-4 py-2 text-sm">Recommended</button>
          <button className="rounded-full border border-border px-4 py-2 text-sm">Price</button>
          <FiltersDialog />
        </div>
      </header>
      <ResultsLayout listings={listings} />
    </div>
  );
}
