import Link from 'next/link';
import { getListings } from '@/lib/api-client';
import { ListingCard } from '@/components/listing/listing-card';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { getMessages } from '@/lib/i18n';

export default async function HomePage({ params: { locale } }: { params: { locale: string } }) {
  const messages = getMessages(locale);
  const all = await getListings();
  const featured = all.filter((listing) => listing.featured);

  return (
    <div className="flex flex-col gap-12">
      <section className="grid gap-8 rounded-3xl bg-surface/70 p-10 shadow-sm lg:grid-cols-[2fr_1fr]">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-ink">{messages.home.title}</h1>
          <p className="mt-4 max-w-xl text-lg text-muted-ink">{messages.home.subtitle}</p>
          <div className="mt-6 flex gap-4">
            <Button asChild>
              <Link href={`/${locale}/search`}>Start exploring</Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href={`/${locale}/host`}>List your home</Link>
            </Button>
          </div>
        </div>
        <Card className="border-none bg-brand text-brand-contrast">
          <CardHeader>
            <CardTitle className="text-2xl font-semibold">Summer Sail Week</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Save 15% on waterfront stays when you book 4+ nights before June 1.</p>
            <Button variant="secondary" className="mt-6 bg-brand-contrast text-brand">
              View details
            </Button>
          </CardContent>
        </Card>
      </section>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-ink">Featured homes</h2>
          <Button variant="ghost" asChild>
            <Link href={`/${locale}/search`}>View all</Link>
          </Button>
        </div>
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {featured.map((listing) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      </section>
      <section className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Stay inspired</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-ink">
            Discover categories like waterfront lofts, desert domes, and alpine cabins curated for your travel mood.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Host spotlight</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-ink">
            HarborHomes hosts receive onboarding support, personalized pricing tips, and 24/7 guest assistance.
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
