import Link from "next/link";
import { listings } from "@/lib/mock-data";
import { ListingCard } from "@/components/listings/listing-card";
import { Button } from "@/components/ui/button";
import { SearchPill } from "@/components/search/search-pill";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { getTranslations } from "next-intl/server";

const categories = [
  { label: "Coastal retreats", emoji: "🌊" },
  { label: "Mountain cabins", emoji: "🏔️" },
  { label: "Creative hubs", emoji: "🎨" },
  { label: "Family escapes", emoji: "👨‍👩‍👧" },
  { label: "Pet-friendly", emoji: "🐾" }
];

export default async function HomePage() {
  const t = await getTranslations("home");
  const featured = listings.filter((listing) => listing.featured);

  return (
    <div className="space-y-20">
      <section className="relative overflow-hidden bg-gradient-to-br from-brand/10 via-white to-surface">
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-12 px-6 py-24 md:flex-row md:items-center">
          <div className="flex-1 space-y-6">
            <Badge variant="brand">HarborHomes</Badge>
            <h1 className="text-4xl font-semibold md:text-5xl">{t("headline")}</h1>
            <p className="max-w-xl text-lg text-muted-ink">{t("subheadline")}</p>
            <div className="max-w-lg">
              <SearchPill variant="stacked" />
            </div>
            <div className="flex flex-wrap gap-3 text-sm text-muted-ink">
              {categories.map((category) => (
                <span key={category.label} className="rounded-full border border-border px-4 py-1">
                  {category.emoji} {category.label}
                </span>
              ))}
            </div>
          </div>
          <div className="relative hidden h-[320px] w-full max-w-md overflow-hidden rounded-3xl border border-border shadow-lg md:block">
            <Image
              src="https://images.unsplash.com/photo-1505691938895-1758d7feb511"
              alt="HarborHomes guests enjoying a curated stay"
              fill
              className="object-cover"
              priority
            />
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-6">
        <header className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold">{t("featured")}</h2>
          <Button variant="ghost" asChild>
            <Link href="/search">View all</Link>
          </Button>
        </header>
        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {featured.map((listing) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      </section>
      <section className="bg-surface py-16">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-6 px-6 text-center">
          <h2 className="text-3xl font-semibold">{t("promo")}</h2>
          <p className="max-w-2xl text-muted-ink">
            Members receive flexible checkout, dedicated trip planners, and partner perks with local artisans.
          </p>
          <Button size="lg">Explore HarborHomes+</Button>
        </div>
      </section>
    </div>
  );
}
