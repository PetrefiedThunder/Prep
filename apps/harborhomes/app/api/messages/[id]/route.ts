import { NextResponse } from 'next/server';
import { threads } from '@/lib/mock-data';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const thread = threads.find((item) => item.id === params.id);
  if (!thread) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  return NextResponse.json(thread);
}
