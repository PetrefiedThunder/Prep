import { wishlists, listings } from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';

export default function WishlistsPage() {
  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Wishlists</h1>
          <p className="text-sm text-muted-ink">Save HarborHomes you love.</p>
        </div>
        <Button variant="secondary">Create wishlist</Button>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        {wishlists.map((wishlist) => {
          const cover = listings.find((listing) => listing.id === wishlist.listingIds[0]);
          return (
            <Card key={wishlist.id}>
              <CardHeader>
                <CardTitle>{wishlist.name}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-ink">
                {wishlist.listingIds.length} homes · {wishlist.isPrivate ? 'Private' : 'Shared'}
                {cover ? <p className="mt-2 text-ink">Featured: {cover.title}</p> : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
