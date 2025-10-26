import { NextResponse } from "next/server";
import { reviews } from "@/lib/mock-data";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const listingId = url.searchParams.get("listingId");
  const filtered = listingId ? reviews.filter((review) => review.listingId === listingId) : reviews;
  return NextResponse.json({ items: filtered });
}
