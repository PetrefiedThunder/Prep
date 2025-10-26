import { listings } from "@/lib/mock-data";
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function HostListingManager({ params }: { params: { id: string } }) {
  const listing = listings.find((item) => item.id === params.id);
  if (!listing) return notFound();

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-brand">Listing manager</p>
          <h1 className="text-3xl font-semibold">{listing.title}</h1>
        </div>
        <Button variant="secondary">Preview listing</Button>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-3 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Details</h2>
          <p className="text-sm text-muted-ink">Update description, highlights, and house rules.</p>
          <Button variant="ghost" size="sm">
            Edit details
          </Button>
        </section>
        <section className="space-y-3 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Photos</h2>
          <p className="text-sm text-muted-ink">Manage gallery order, add hero, and alt text.</p>
          <Button variant="ghost" size="sm">
            Edit photos
          </Button>
        </section>
        <section className="space-y-3 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Pricing & discounts</h2>
          <p className="text-sm text-muted-ink">Set nightly rate, weekly stays, and promotions.</p>
          <Button variant="ghost" size="sm">
            Adjust pricing
          </Button>
        </section>
        <section className="space-y-3 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Availability</h2>
          <p className="text-sm text-muted-ink">Block dates, sync calendars, and configure instant book.</p>
          <Button variant="ghost" size="sm">
            Edit availability
          </Button>
        </section>
      </div>
    </div>
  );
}
