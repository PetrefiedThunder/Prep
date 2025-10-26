import Link from 'next/link';
import { listings } from '@/lib/mock-data';
import { RevenueSparkline } from '@/components/analytics/revenue-sparkline';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';

export default function HostDashboard({ params: { locale } }: { params: { locale: string } }) {
  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Host dashboard</h1>
          <p className="text-sm text-muted-ink">Track your HarborHomes performance.</p>
        </div>
        <Button asChild>
          <Link href={`/${locale}/host/new`}>Create listing</Link>
        </Button>
      </header>
      <section>
        <RevenueSparkline className="max-w-xl" />
      </section>
      <section className="grid gap-6 md:grid-cols-2">
        {listings.map((listing) => (
          <Card key={listing.id}>
            <CardHeader>
              <CardTitle>{listing.title}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 text-sm text-muted-ink">
              <p>Status: Published</p>
              <p>{listing.reviewCount} reviews · {listing.rating.toFixed(2)} rating</p>
              <Button asChild variant="secondary">
                <Link href={`/${locale}/host/listing/${listing.id}`}>Manage</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}
