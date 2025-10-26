import { NextResponse } from "next/server";
import { wishlists } from "@/lib/mock-data";

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const wishlist = wishlists.find((item) => item.id === params.id);
  if (!wishlist) {
    return NextResponse.json({ message: "Wishlist not found" }, { status: 404 });
  }
  return NextResponse.json(wishlist);
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const payload = await request.json();
  const wishlist = wishlists.find((item) => item.id === params.id);
  if (!wishlist) {
    return NextResponse.json({ message: "Wishlist not found" }, { status: 404 });
  }
  wishlist.name = payload.name ?? wishlist.name;
  wishlist.isPrivate = payload.isPrivate ?? wishlist.isPrivate;
  wishlist.listingIds = payload.listingIds ?? wishlist.listingIds;
  return NextResponse.json(wishlist);
}
