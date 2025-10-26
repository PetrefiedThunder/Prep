import { notFound } from 'next/navigation';
import { listings, reviews } from '@/lib/mock-data';
import { ListingGallery } from '@/components/listing/listing-gallery';
import { BookingCard } from '@/components/listing/booking-card';
import { Badge, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';

export default function ListingDetail({ params: { id } }: { params: { id: string } }) {
  const listing = listings.find((item) => item.id === id);
  if (!listing) notFound();
  const listingReviews = reviews.filter((review) => review.listingId === id);

  return (
    <div className="grid gap-12 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-10">
        <ListingGallery photos={listing.photos} />
        <section className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold text-ink">{listing.title}</h1>
              <p className="text-sm text-muted-ink">
                {listing.city}, {listing.country}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {listing.tags.map((tag) => (
                <Badge key={tag}>{tag}</Badge>
              ))}
            </div>
          </div>
          <p className="text-base text-muted-ink">{listing.description}</p>
        </section>
        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-ink">Amenities</h2>
          <ul className="grid grid-cols-2 gap-3 text-sm text-muted-ink">
            {listing.amenities.map((amenity) => (
              <li key={amenity} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-brand" />
                {amenity.replace('-', ' ')}
              </li>
            ))}
          </ul>
        </section>
        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-ink">Reviews</h2>
          <div className="grid gap-4">
            {listingReviews.map((review) => (
              <Card key={review.id}>
                <CardHeader>
                  <CardTitle className="text-base font-semibold">{review.author}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-ink">{review.body}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </div>
      <BookingCard listingId={listing.id} pricePerNight={listing.pricePerNight} />
    </div>
  );
}
