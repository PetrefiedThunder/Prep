import type { Listing, MessageThread, Review, Wishlist } from "@/lib/types";

export async function fetchListings(query: string): Promise<{ items: Listing[]; total: number }> {
  const response = await fetch(`/api/listings${query}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load listings");
  return response.json();
}

export async function fetchListing(id: string): Promise<Listing> {
  const response = await fetch(`/api/listings/${id}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Listing not found");
  return response.json();
}

export async function fetchReviews(listingId: string): Promise<Review[]> {
  const response = await fetch(`/api/reviews?listingId=${listingId}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load reviews");
  const payload = await response.json();
  return payload.items;
}

export async function fetchWishlists(): Promise<Wishlist[]> {
  const response = await fetch(`/api/wishlists`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load wishlists");
  const payload = await response.json();
  return payload.items;
}

export async function fetchMessages(): Promise<MessageThread[]> {
  const response = await fetch(`/api/messages`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load messages");
  const payload = await response.json();
  return payload.items;
}
