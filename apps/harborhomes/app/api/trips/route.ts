import { NextRequest, NextResponse } from 'next/server';
import { trips as MOCK_TRIPS } from '@/lib/mock-data';

// GET /api/trips - returns trips for the current user (mocked; upstream recommended)
export async function GET(_req: NextRequest) {
  const baseEnv = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/+$/, '');
  const upstream = process.env.TRIPS_UPSTREAM || (baseEnv ? `${baseEnv}/api/v1/trips` : undefined);

  if (!upstream) {
    return NextResponse.json(MOCK_TRIPS, { status: 200 });
  }

  try {
    const res = await fetch(upstream, { headers: { Accept: 'application/json' }, cache: 'no-store' });
    if (!res.ok) {
      return NextResponse.json(MOCK_TRIPS, { status: 200 });
    }
    const payload = await res.json();
    const items = Array.isArray(payload)
      ? payload
      : Array.isArray(payload?.trips)
      ? payload.trips
      : Array.isArray(payload?.data)
      ? payload.data
      : [];
    return NextResponse.json(items.length ? items : MOCK_TRIPS, { status: 200 });
  } catch {
    return NextResponse.json(MOCK_TRIPS, { status: 200 });
  }
}
