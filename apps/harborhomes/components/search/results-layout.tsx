'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';
import { ListingCard } from '@/components/listing/listing-card';
import type { Listing } from '@/lib/types';
import { Skeleton } from '@/components/ui';

const Map = dynamic(() => import('@/components/search/search-map').then((mod) => mod.SearchMap), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />
});

export interface ResultsLayoutProps {
  listings: Listing[];
}

export const ResultsLayout = ({ listings }: ResultsLayoutProps) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedListing = useMemo(
    () => listings.find((listing) => listing.id === selectedId) ?? listings[0],
    [listings, selectedId]
  );

  useEffect(() => {
    if (!selectedId && listings.length) {
      setSelectedId(listings[0]?.id ?? null);
    }
  }, [listings, selectedId]);

  return (
    <div className="grid h-[calc(100vh-6rem)] gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-4 overflow-y-auto pr-4">
        {listings.map((listing) => (
          <ListingCard
            key={listing.id}
            listing={listing}
            selected={listing.id === selectedId}
            onHover={() => setSelectedId(listing.id)}
          />
        ))}
      </div>
      <div className="hidden overflow-hidden rounded-3xl border border-border/80 lg:block">
        <Map listings={listings} selectedId={selectedId} onSelect={setSelectedId} focusListing={selectedListing} />
      </div>
    </div>
  );
};
