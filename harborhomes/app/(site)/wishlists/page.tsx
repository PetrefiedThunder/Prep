import { wishlists, listings } from "@/lib/mock-data";
import { ListingCard } from "@/components/listings/listing-card";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Wishlists"
};

export default function WishlistsPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Saved escapes</h1>
          <p className="text-muted-ink">Keep track of HarborHomes you're dreaming about.</p>
        </div>
        <Button variant="secondary">Create new wishlist</Button>
      </header>
      <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {wishlists.map((wishlist) => {
          const homes = listings.filter((listing) => wishlist.listingIds.includes(listing.id));
          return (
            <div key={wishlist.id} className="space-y-4 rounded-3xl border border-border bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{wishlist.name}</h2>
                  <p className="text-xs text-muted-ink">{wishlist.isPrivate ? "Private" : "Shared"}</p>
                </div>
                <Button variant="ghost" size="sm">
                  Share
                </Button>
              </div>
              <div className="grid gap-3">
                {homes.map((listing) => (
                  <ListingCard key={listing.id} listing={listing} />
                ))}
                {!homes.length && (
                  <div className="rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted-ink">
                    Add HarborHomes to see them here.
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
