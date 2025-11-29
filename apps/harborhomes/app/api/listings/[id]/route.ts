import { NextResponse } from 'next/server';
import { listings as MOCK_LISTINGS } from '@/lib/mock-data';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const id = params.id;
  const baseEnv = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/+$/, '');
  const upstream = process.env.LISTING_UPSTREAM || (baseEnv ? `${baseEnv}/api/v1/listings/${encodeURIComponent(id)}` : undefined);

  if (!upstream) {
    const listing = MOCK_LISTINGS.find((item) => item.id === id);
    return listing ? NextResponse.json(listing, { status: 200 }) : NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  try {
    const res = await fetch(upstream, { headers: { Accept: 'application/json' }, cache: 'no-store' });
    if (!res.ok) {
      const listing = MOCK_LISTINGS.find((item) => item.id === id);
      return listing ? NextResponse.json(listing, { status: 200 }) : NextResponse.json({ error: 'Not found' }, { status: 404 });
    }
    const payload = await res.json();
    return NextResponse.json(payload, { status: 200 });
  } catch {
    const listing = MOCK_LISTINGS.find((item) => item.id === id);
    return listing ? NextResponse.json(listing, { status: 200 }) : NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
}
