import { NextResponse } from 'next/server';
import { wishlists } from '@/lib/mock-data';

export async function GET() {
  return NextResponse.json({ wishlists });
}
