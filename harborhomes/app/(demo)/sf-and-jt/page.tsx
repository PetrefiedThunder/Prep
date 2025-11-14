import type { Metadata } from "next";

import { FeeCard, PermitBadge, RequirementsList } from "@/components/prep";
import { fetchCityCompliance, type CityCompliance } from "@/lib/compliance";

const CITY_CONFIGS = [
  {
    slug: "san-francisco",
    title: "San Francisco, CA",
    summary: "Track Department of Public Health filings, renewal fees, and on-site inspections for the Bay Area flagship kitchen."
  },
  {
    slug: "joshua-tree",
    title: "Joshua Tree, CA",
    summary: "Monitor San Bernardino County requirements to keep high-desert retreat experiences fully licensed and audit-ready."
  }
] as const;

type CityConfig = (typeof CITY_CONFIGS)[number];

type CityResult = {
  config: CityConfig;
  compliance: CityCompliance | null;
  error?: string;
};

export const metadata: Metadata = {
  title: "San Francisco & Joshua Tree permitting overview",
  description:
    "Compare HarborHomes compliance requirements across San Francisco and Joshua Tree with live data hydrated via your configured COMPLIANCE_API_BASE endpoint."
};

function formatError(error: unknown) {
  if (error instanceof Error) {
    if (error.message.includes("COMPLIANCE_API_BASE")) {
      return "Set COMPLIANCE_API_BASE (or NEXT_PUBLIC_API_BASE) to the base URL of your compliance API to stream live data.";
    }
    return error.message;
  }

  return "Something went wrong while loading the compliance feed.";
}

async function loadCity(config: CityConfig): Promise<CityResult> {
  try {
    const compliance = await fetchCityCompliance(config.slug);
    return { config, compliance };
  } catch (error) {
    return { config, compliance: null, error: formatError(error) };
  }
}

export default async function SfAndJtPage() {
  const cities = await Promise.all(CITY_CONFIGS.map((config) => loadCity(config)));

  return (
    <div className="bg-bg">
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-6 py-12 lg:px-8 lg:py-16">
        <header className="space-y-4 text-center lg:text-left">
          <p className="text-sm font-semibold uppercase tracking-wide text-brand">Compliance automation</p>
          <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">San Francisco ↔ Joshua Tree</h1>
          <p className="mx-auto max-w-3xl text-sm text-muted-ink sm:text-base lg:mx-0">
            HarborHomes pulls city and county requirements directly from your configured compliance API. Update
            <code className="mx-1 rounded bg-surface px-1.5 py-0.5 text-xs">COMPLIANCE_API_BASE</code>
            to point at the desired environment and we&apos;ll hydrate these cards on every visit.
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-2">
          {cities.map(({ config, compliance, error }) => (
            <section
              key={config.slug}
              aria-labelledby={`${config.slug}-heading`}
              className="space-y-6 rounded-3xl border border-border bg-white p-6 shadow-sm"
            >
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1">
                    <h2 id={`${config.slug}-heading`} className="text-2xl font-semibold text-ink">
                      {config.title}
                    </h2>
                    <p className="text-sm text-muted-ink">{config.summary}</p>
                  </div>
                  {compliance ? (
                    <PermitBadge validation={compliance.validation} totals={compliance.totals} />
                  ) : (
                    <div className="rounded-2xl border border-dashed border-border bg-surface px-4 py-3 text-left text-sm text-muted-ink">
                      Awaiting compliance feed
                    </div>
                  )}
                </div>

                {compliance ? (
                  <RequirementsList items={compliance.paperwork} />
                ) : (
                  <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-muted-ink">
                    <p className="font-medium text-ink">Unable to load compliance data</p>
                    <p className="mt-1 leading-relaxed">
                      {error ?? "Data will populate once your compliance API responds successfully."}
                    </p>
                  </div>
                )}
              </div>

              {compliance && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-ink">Fee schedule</h3>
                  <div className="grid gap-4">
                    {compliance.fees.map((fee) => (
                      <FeeCard key={fee.name} fee={fee} highlight={fee.kind === "recurring"} />
                    ))}
                  </div>
                </div>
              )}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
