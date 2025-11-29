import 'server-only';
import type { Listing, Review, Trip } from '@/lib/types';

export async function getListings(): Promise<Listing[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/api/listings`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store'
  });
  if (!res.ok) {
    throw new Error(`Failed to load listings (${res.status})`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : Array.isArray(data?.listings) ? data.listings : Array.isArray(data?.data) ? data.data : [];
}

export async function getListingById(id: string): Promise<Listing | null> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/api/listings/${encodeURIComponent(id)}`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store'
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load listing ${id} (${res.status})`);
  return await res.json();
}

export async function getReviews(listingId: string): Promise<Review[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/api/reviews?listingId=${encodeURIComponent(listingId)}`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store'
  });
  if (!res.ok) throw new Error(`Failed to load reviews (${res.status})`);
  const data = await res.json();
  return Array.isArray(data) ? data : Array.isArray(data?.reviews) ? data.reviews : Array.isArray(data?.data) ? data.data : [];
}

export async function getTrips(): Promise<Trip[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/api/trips`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store'
  });
  if (!res.ok) throw new Error(`Failed to load trips (${res.status})`);
  const data = await res.json();
  return Array.isArray(data) ? data : Array.isArray(data?.trips) ? data.trips : Array.isArray(data?.data) ? data.data : [];
}
