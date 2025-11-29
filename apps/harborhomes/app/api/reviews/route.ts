import { NextRequest, NextResponse } from 'next/server';
import { reviews as MOCK_REVIEWS } from '@/lib/mock-data';

// GET /api/reviews?listingId=...
// Proxies to upstream if configured, otherwise serves mock reviews.
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const listingId = url.searchParams.get('listingId') ?? undefined;

  const baseEnv = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/+$/, '');
  const upstreamBase = process.env.REVIEWS_UPSTREAM || (baseEnv ? `${baseEnv}/api/v1/reviews` : undefined);

  if (!upstreamBase) {
    const filtered = listingId ? MOCK_REVIEWS.filter((r) => r.listingId === listingId) : MOCK_REVIEWS;
    return NextResponse.json(filtered, { status: 200 });
  }

  const target = listingId ? `${upstreamBase}?listingId=${encodeURIComponent(listingId)}` : upstreamBase;
  try {
    const res = await fetch(target, { headers: { Accept: 'application/json' }, cache: 'no-store' });
    if (!res.ok) {
      const filtered = listingId ? MOCK_REVIEWS.filter((r) => r.listingId === listingId) : MOCK_REVIEWS;
      return NextResponse.json(filtered, { status: 200 });
    }
    const payload = await res.json();
    const items = Array.isArray(payload)
      ? payload
      : Array.isArray(payload?.reviews)
      ? payload.reviews
      : Array.isArray(payload?.data)
      ? payload.data
      : [];
    return NextResponse.json(items.length ? items : MOCK_REVIEWS, { status: 200 });
  } catch {
    const filtered = listingId ? MOCK_REVIEWS.filter((r) => r.listingId === listingId) : MOCK_REVIEWS;
    return NextResponse.json(filtered, { status: 200 });
  }
}
