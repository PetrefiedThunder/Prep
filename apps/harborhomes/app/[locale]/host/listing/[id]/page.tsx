import { notFound } from 'next/navigation';
import { listings } from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';

export default function HostListingManager({ params: { id } }: { params: { id: string } }) {
  const listing = listings.find((item) => item.id === id);
  if (!listing) notFound();

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Manage {listing.title}</h1>
          <p className="text-sm text-muted-ink">Update details, pricing, and availability.</p>
        </div>
        <Button variant="secondary">Preview listing</Button>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-ink">
            Beds: {listing.beds} · Baths: {listing.baths} · Guests: {listing.guests}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Pricing & discounts</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-ink">
            Nightly rate: {listing.pricePerNight}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Availability</CardTitle>
          </CardHeader>
          <CardContent className="h-48 rounded-3xl border border-dashed border-border" />
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Policies</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-ink">Flexible cancellation · Self check-in</CardContent>
        </Card>
      </div>
    </div>
  );
}
