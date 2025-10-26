import { NextResponse } from "next/server";
import { listings } from "@/lib/mock-data";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.get("q")?.toLowerCase();
  const minPrice = Number(url.searchParams.get("minPrice") ?? "0");
  const maxPrice = Number(url.searchParams.get("maxPrice") ?? "10000");
  const guests = Number(url.searchParams.get("guests") ?? "0");
  const amenities = url.searchParams.getAll("amenities");

  const filtered = listings.filter((listing) => {
    const matchesQuery = query
      ? [listing.title, listing.city, listing.country]
          .join(" ")
          .toLowerCase()
          .includes(query)
      : true;
    const matchesPrice = listing.nightlyPrice >= minPrice && listing.nightlyPrice <= maxPrice;
    const matchesGuests = guests ? listing.guests >= guests : true;
    const matchesAmenities = amenities.length
      ? amenities.every((amenity) => listing.amenities.includes(amenity))
      : true;

    return matchesQuery && matchesPrice && matchesGuests && matchesAmenities;
  });

  return NextResponse.json({ items: filtered, total: filtered.length });
}
