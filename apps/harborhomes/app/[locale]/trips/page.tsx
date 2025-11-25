import { getTrips, getListings } from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';
import { format } from 'date-fns';

export default async function TripsPage() {
  const [trips, listings] = await Promise.all([getTrips(), getListings()]);
  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Your trips</h1>
          <p className="text-sm text-muted-ink">Manage upcoming and past stays.</p>
        </div>
        <Button variant="secondary">Download receipt</Button>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        {trips.map((trip) => {
          const listing = listings.find((item) => item.id === trip.listingId);
          return (
            <Card key={trip.id}>
              <CardHeader>
                <CardTitle>{listing?.title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-ink">
                <p>
                  {format(new Date(trip.startDate), 'MMM d, yyyy')} – {format(new Date(trip.endDate), 'MMM d, yyyy')}
                </p>
                <p className="mt-2 capitalize">Status: {trip.status}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
