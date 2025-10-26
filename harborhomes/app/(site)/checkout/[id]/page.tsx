import { listings } from "@/lib/mock-data";
import { notFound } from "next/navigation";
import { CheckoutFlow } from "@/components/checkout/checkout-flow";
import { getTranslations } from "next-intl/server";

export default async function CheckoutPage({ params, searchParams }: { params: { id: string }; searchParams: Record<string, string | string[] | undefined> }) {
  const listing = listings.find((item) => item.id === params.id);
  if (!listing) return notFound();
  const getParam = (key: string) => {
    const value = searchParams[key];
    return Array.isArray(value) ? value[0] : value;
  };
  const start = getParam("start") ?? new Date().toISOString();
  const end = getParam("end") ?? new Date(Date.now() + 86400000).toISOString();
  const guests = Number(getParam("guests") ?? "2");
  const t = await getTranslations("checkout");

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10 space-y-2">
        <p className="text-sm uppercase tracking-wide text-brand">{t("review")}</p>
        <h1 className="text-3xl font-semibold">Finalize your HarborHome booking</h1>
        <p className="text-muted-ink">{listing.title}</p>
      </header>
      <CheckoutFlow listing={listing} startDate={start} endDate={end} guests={guests} />
    </div>
  );
}
