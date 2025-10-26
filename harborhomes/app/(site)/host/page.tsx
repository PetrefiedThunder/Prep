import { hostListings } from "@/lib/mock-data";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/currency";

export const metadata = { title: "Host dashboard" };

export default function HostDashboard() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">HarborHomes Hosting</h1>
          <p className="text-muted-ink">Insights, earnings, and quick actions for your listings.</p>
        </div>
        <Button asChild>
          <a href="/host/new">Create a listing</a>
        </Button>
      </header>
      <div className="mt-10 grid gap-6 md:grid-cols-2">
        {hostListings.map((summary) => {
          return (
            <article key={summary.id} className="space-y-4 rounded-3xl border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{summary.title}</h2>
                  <p className="text-xs uppercase tracking-wide text-muted-ink">{summary.status}</p>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <a href={`/host/listing/${summary.id}`}>Manage</a>
                </Button>
              </div>
              <dl className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <dt className="text-muted-ink">Views</dt>
                  <dd className="text-lg font-semibold">{summary.views}</dd>
                </div>
                <div>
                  <dt className="text-muted-ink">Bookings</dt>
                  <dd className="text-lg font-semibold">{summary.bookings}</dd>
                </div>
                <div>
                  <dt className="text-muted-ink">Revenue</dt>
                  <dd className="text-lg font-semibold">{formatCurrency(summary.revenue)}</dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>
    </div>
  );
}
