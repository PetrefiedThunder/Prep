import { NextResponse } from "next/server";
import { listings } from "@/lib/mock-data";

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const listing = listings.find((item) => item.id === params.id);
  if (!listing) {
    return NextResponse.json({ message: "Listing not found" }, { status: 404 });
  }
  return NextResponse.json(listing);
}
