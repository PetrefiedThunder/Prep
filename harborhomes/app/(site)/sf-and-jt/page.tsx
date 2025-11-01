import type { Metadata } from "next";
import { FeeCard, PermitBadge, RequirementsList } from "@/components/compliance";
import { fetchCityCompliance } from "@/lib/compliance";

const CITIES = [
  { slug: "san-francisco", title: "San Francisco", intro: "Track Department of Public Health filings and renewals." },
  { slug: "joshua-tree", title: "Joshua Tree", intro: "Monitor county health submissions for desert retreat pop-ups." }
] as const;

export const metadata: Metadata = {
  title: "San Francisco & Joshua Tree permitting",
  description: "Compare HarborHomes compliance requirements across San Francisco and Joshua Tree."
};

export default async function SfAndJtPage() {
  const cityData = await Promise.all(CITIES.map((city) => fetchCityCompliance(city.slug)));
  const cityEntries = CITIES.map((city, index) => ({ config: city, data: cityData[index] }));

  return (
    <div className="bg-bg">
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-6 py-12">
        <header className="space-y-4">
          <p className="text-sm uppercase tracking-wide text-brand">Permitting overview</p>
          <h1 className="text-3xl font-semibold text-ink">San Francisco & Joshua Tree</h1>
          <p className="max-w-3xl text-muted-ink">
            HarborHomes streamlines paperwork across iconic urban kitchens and high-desert pop-ups. Review fees, paperwork, and
            permit status for both jurisdictions in one view.
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-2">
          {cityEntries.map(({ config, data }) => (
            <section key={config.slug} className="space-y-6 rounded-3xl border border-border bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-2xl font-semibold text-ink">{config.title}</h2>
                    <p className="text-sm text-muted-ink">{config.intro}</p>
                  </div>
                  <PermitBadge validation={data.validation} totals={data.totals} />
                </div>
                <RequirementsList items={data.paperwork} />
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-ink">Fee schedule</h3>
                <div className="grid gap-4">
                  {data.fees.map((fee) => (
                    <FeeCard key={fee.name} fee={fee} highlight={fee.kind === "recurring"} />
                  ))}
                </div>
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
