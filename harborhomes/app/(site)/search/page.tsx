import { SearchResults } from "@/components/search/search-results";
import { getTranslations } from "next-intl/server";

export const metadata = {
  title: "Search HarborHomes"
};

export default async function SearchPage() {
  const t = await getTranslations("search");

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-brand">{t("title")}</p>
        <h1 className="text-3xl font-semibold">Curated stays around the globe</h1>
        <p className="max-w-2xl text-muted-ink">
          Explore HarborHomes stays with flexible filters, instant booking, and real-time map updates.
        </p>
      </header>
      <SearchResults />
    </div>
  );
}
