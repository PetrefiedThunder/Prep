import { NextRequest, NextResponse } from 'next/server';
import { listings as MOCK_LISTINGS } from '@/lib/mock-data';

// Proxy listings to an upstream service if configured.
// Prefer LISTINGS_UPSTREAM (full URL), otherwise try NEXT_PUBLIC_API_BASE + /api/v1/listings.
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const q = url.searchParams.get('q')?.toLowerCase();

  const baseEnv = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/+$/, '');
  const upstream = process.env.LISTINGS_UPSTREAM || (baseEnv ? `${baseEnv}/api/v1/listings` : undefined);

  // If no upstream configured, serve filtered mock data
  if (!upstream) {
    const items = q
      ? MOCK_LISTINGS.filter((listing) =>
          [listing.title, listing.city, listing.country].some((field) => field.toLowerCase().includes(q!))
        )
      : MOCK_LISTINGS;
    return NextResponse.json(items, { status: 200 });
  }

  try {
    const res = await fetch(upstream, {
      headers: { Accept: 'application/json' },
      cache: 'no-store'
    });

    // Upstream failed → fallback to mock
    if (!res.ok) {
      const items = q
        ? MOCK_LISTINGS.filter((listing) =>
            [listing.title, listing.city, listing.country].some((field) => field.toLowerCase().includes(q!))
          )
        : MOCK_LISTINGS;
      return NextResponse.json(items, { status: 200 });
    }

    const payload = await res.json();
    const upstreamItems = Array.isArray(payload)
      ? payload
      : Array.isArray(payload?.listings)
      ? payload.listings
      : Array.isArray(payload?.data)
      ? payload.data
      : [];

    const items = upstreamItems.length
      ? (q
          ? upstreamItems.filter((listing: any) =>
              [listing.title, listing.city, listing.country]
                .filter(Boolean)
                .some((field: string) => field.toLowerCase().includes(q!))
            )
          : upstreamItems)
      : MOCK_LISTINGS;

    return NextResponse.json(items, { status: 200 });
  } catch {
    const items = q
      ? MOCK_LISTINGS.filter((listing) =>
          [listing.title, listing.city, listing.country].some((field) => field.toLowerCase().includes(q!))
        )
      : MOCK_LISTINGS;
    return NextResponse.json(items, { status: 200 });
  }
}
