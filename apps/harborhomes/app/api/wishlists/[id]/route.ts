import { NextResponse } from 'next/server';
import { wishlists } from '@/lib/mock-data';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const wishlist = wishlists.find((item) => item.id === params.id);
  if (!wishlist) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  return NextResponse.json(wishlist);
}
