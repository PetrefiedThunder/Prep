import { NextResponse } from 'next/server';
import { listings } from '@/lib/mock-data';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const q = url.searchParams.get('q');
  const filtered = q
    ? listings.filter((listing) =>
        [listing.title, listing.city, listing.country].some((field) => field.toLowerCase().includes(q.toLowerCase()))
      )
    : listings;
  return NextResponse.json({ listings: filtered });
}
