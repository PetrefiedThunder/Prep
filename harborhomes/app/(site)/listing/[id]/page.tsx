import { listings } from "@/lib/mock-data";
import { notFound } from "next/navigation";
import { ListingGallery } from "@/components/listings/listing-gallery";
import { BookingCard } from "@/components/listings/booking-card";
import { reviews } from "@/lib/mock-data";
import { ReviewSummary } from "@/components/listings/review-summary";
import { getTranslations } from "next-intl/server";
import { formatCurrency } from "@/lib/currency";
import dynamic from "next/dynamic";

const Mapbox = dynamic(() => import("@/components/map/mapbox").then((mod) => mod.Mapbox), { ssr: false });

export async function generateMetadata({ params }: { params: { id: string } }) {
  const listing = listings.find((item) => item.id === params.id);
  if (!listing) return {};
  return {
    title: `${listing.title} | HarborHomes`,
    description: listing.description
  };
}

export default async function ListingPage({ params }: { params: { id: string } }) {
  const listing = listings.find((item) => item.id === params.id);
  if (!listing) return notFound();
  const listingReviews = reviews.filter((review) => review.listingId === listing.id);
  const t = await getTranslations("listing");

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-12 px-6 py-12">
      <div className="space-y-3">
        <h1 className="text-3xl font-semibold">{listing.title}</h1>
        <p className="text-muted-ink">
          {listing.city}, {listing.country} · {formatCurrency(listing.nightlyPrice)} {t("night")}
        </p>
      </div>
      <ListingGallery images={listing.images} title={listing.title} />
      <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-10">
          <section className="rounded-3xl border border-border bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">About this stay</h2>
            <p className="mt-3 text-muted-ink">{listing.description}</p>
            <div className="mt-6 grid gap-3 text-sm">
              {listing.highlights.map((highlight) => (
                <div key={highlight} className="rounded-2xl bg-surface px-4 py-3 text-ink">
                  {highlight}
                </div>
              ))}
            </div>
          </section>
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">Amenities</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {listing.amenities.map((amenity) => (
                <div key={amenity} className="rounded-2xl border border-border px-4 py-3 text-sm text-ink">
                  {amenity}
                </div>
              ))}
            </div>
          </section>
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">{t("policies")}</h2>
            <p className="text-sm text-muted-ink">{listing.policies.cancellation}</p>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-ink">
              {listing.policies.houseRules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </section>
          <ReviewSummary reviews={listingReviews} />
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">Neighborhood</h2>
            <p className="text-muted-ink">{listing.neighborhood}</p>
            <div className="h-64 overflow-hidden rounded-3xl">
              <Mapbox listings={[listing]} selectedId={listing.id} />
            </div>
          </section>
        </div>
        <BookingCard listing={listing} />
      </div>
    </div>
  );
}
