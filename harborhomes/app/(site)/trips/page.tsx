import { trips, listings } from "@/lib/mock-data";
import { formatDateRange } from "@/lib/dates";
import { formatCurrency } from "@/lib/currency";
import Image from "next/image";

export const metadata = { title: "Trips" };

export default function TripsPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Your voyages</h1>
      <p className="text-muted-ink">Upcoming and past HarborHomes stays with receipts.</p>
      <div className="mt-8 space-y-6">
        {trips.map((trip) => {
          const listing = listings.find((item) => item.id === trip.listingId);
          if (!listing) return null;
          return (
            <article key={trip.id} className="flex flex-col gap-4 rounded-3xl border border-border bg-white p-6 shadow-sm md:flex-row">
              <div className="relative h-40 w-full overflow-hidden rounded-2xl md:w-48">
                <Image src={listing.images[0]} alt={listing.title} fill className="object-cover" sizes="200px" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold">{listing.title}</h2>
                <p className="text-sm text-muted-ink">{formatDateRange(trip.startDate, trip.endDate)}</p>
                <p className="mt-2 text-sm text-muted-ink">{trip.guests} guests · Total {formatCurrency(trip.total)}</p>
                <button className="mt-4 text-sm font-semibold text-brand">View receipt</button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
