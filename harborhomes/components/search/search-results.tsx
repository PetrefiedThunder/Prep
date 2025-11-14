"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchListings } from "@/lib/api";
import { ListingCard } from "@/components/listings/listing-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useSearchParams } from "next/navigation";
import { track } from "@/lib/analytics";

const Mapbox = dynamic(() => import("@/components/map/mapbox").then((mod) => mod.Mapbox), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-3xl" />
});

const sorts = [
  { value: "recommended", label: "Recommended" },
  { value: "price", label: "Price" },
  { value: "rating", label: "Rating" }
];

export function SearchResults() {
  const params = useSearchParams();
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedSort, setSelectedSort] = useState("recommended");

  const queryString = useMemo(() => {
    const search = new URLSearchParams(params.toString());
    search.set("sort", selectedSort);
    return `?${search.toString()}`;
  }, [params, selectedSort]);

  const { data, isLoading } = useQuery({
    queryKey: ["listings", queryString],
    queryFn: () => fetchListings(queryString),
    staleTime: 1000 * 30
  });

  const listings = data?.items ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(320px,480px)]">
      <div className="space-y-4">
        <div className="sticky top-24 z-20 flex items-center justify-between rounded-2xl border border-border bg-white/90 px-4 py-3 backdrop-blur">
          <div className="text-sm font-semibold">{listings.length} stays</div>
          <div className="flex items-center gap-2">
            {sorts.map((sort) => (
              <Button
                key={sort.value}
                variant={selectedSort === sort.value ? "secondary" : "ghost"}
                size="sm"
                onClick={() => {
                  setSelectedSort(sort.value);
                  track({ type: "filter_apply", filters: { sort: sort.value } });
                }}
              >
                {sort.label}
              </Button>
            ))}
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {isLoading &&
            Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-80 rounded-3xl" />
            ))}
          {listings.map((listing) => (
            <ListingCard key={listing.id} listing={listing} onHover={setHoveredId} />
          ))}
        </div>
      </div>
      <div className="sticky top-28 h-[calc(100vh-140px)] overflow-hidden rounded-3xl">
        <Mapbox listings={listings} selectedId={hoveredId ?? undefined} onSelect={(id) => setHoveredId(id)} />
      </div>
    </div>
  );
}
