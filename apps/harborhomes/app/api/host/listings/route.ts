import { NextResponse } from 'next/server';
import { listings } from '@/lib/mock-data';

export async function GET() {
  return NextResponse.json({ listings });
}
