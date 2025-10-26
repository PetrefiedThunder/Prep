import { NextResponse } from "next/server";
import { wishlists } from "@/lib/mock-data";

export async function GET() {
  return NextResponse.json({ items: wishlists });
}

export async function POST(request: Request) {
  const payload = await request.json();
  const newWishlist = {
    id: `wl-${Date.now()}`,
    name: payload.name ?? "Untitled",
    isPrivate: Boolean(payload.isPrivate),
    listingIds: payload.listingIds ?? []
  };
  wishlists.push(newWishlist);
  return NextResponse.json(newWishlist, { status: 201 });
}
