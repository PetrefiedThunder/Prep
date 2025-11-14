import { NextResponse } from "next/server";
import { wishlists } from "@/lib/mock-data";

/**
 * CRITICAL: This API uses in-memory storage and will lose all data on server restart.
 * TODO: Implement database persistence with proper schema:
 *   - Create wishlists table with id, name, isPrivate, userId, createdAt
 *   - Create wishlist_items junction table for listingIds
 *   - Add authentication to associate wishlists with users
 *   - Add migration files and ORM integration
 * This is a PRODUCTION-BLOCKING issue that must be resolved before launch.
 */

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
