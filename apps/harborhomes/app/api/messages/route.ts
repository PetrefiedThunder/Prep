import { NextResponse } from 'next/server';
import { threads } from '@/lib/mock-data';

export async function GET() {
  return NextResponse.json({ threads });
}
