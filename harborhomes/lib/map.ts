import type { Listing } from "./types";

export function listingsToGeoJSON(listings: Listing[]) {
  return {
    type: "FeatureCollection" as const,
    features: listings.map((listing) => ({
      type: "Feature" as const,
      properties: {
        id: listing.id,
        title: listing.title,
        price: listing.nightlyPrice,
        rating: listing.rating
      },
      geometry: {
        type: "Point" as const,
        coordinates: [listing.coordinates.longitude, listing.coordinates.latitude]
      }
    }))
  };
}
