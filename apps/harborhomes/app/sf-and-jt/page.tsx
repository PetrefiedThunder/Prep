import type { Metadata } from 'next';

import { FeeCard, PermitBadge, RequirementsList } from '@/components';
import { loadCityCompliance } from '@/lib/policy';

export const metadata: Metadata = {
  title: 'Policy snapshots · San Francisco & Joshua Tree',
  description:
    'Compare Prep policy orchestration for San Francisco and Joshua Tree, including fee schedules, outstanding requirements, and active permits.'
};

const CITY_SLUGS = ['san-francisco-ca', 'joshua-tree-ca'] as const;

const loadSnapshots = () => Promise.all(CITY_SLUGS.map((slug) => loadCityCompliance(slug)));

export default async function SfAndJoshuaTreePage() {
  const snapshots = await loadSnapshots();

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-6 py-16 lg:px-8">
      <header className="flex flex-col gap-4 text-center lg:text-left">
        <p className="text-sm font-semibold uppercase tracking-widest text-muted-ink">Prep policy orchestration</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Side-by-side view: San Francisco ↔ Joshua Tree
        </h1>
        <p className="text-base text-muted-ink sm:text-lg">
          Configure <code className="rounded-md bg-muted px-1.5 py-0.5 text-[13px]">NEXT_PUBLIC_API_BASE</code> to stream live policy data from your API Gateway or lean on the embedded snapshots below. Each card showcases the fee stack, compliance tasks, and permit posture that Prep uses when automating onboarding flows.
        </p>
      </header>

      <div className="flex flex-col gap-12">
        {snapshots.map((city) => (
          <section key={city.slug} aria-labelledby={`${city.slug}-heading`} className="flex flex-col gap-6">
            <div className="flex flex-col gap-2 text-center lg:text-left">
              <h2 id={`${city.slug}-heading`} className="text-2xl font-semibold text-ink">
                {city.displayName}
              </h2>
              <p className="text-sm text-muted-ink sm:text-base">{city.summary}</p>
            </div>

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
              <FeeCard
                city={city.city}
                state={city.state}
                updatedAt={city.updatedAt}
                summary="Updated policy fee schedule"
                fees={city.fees}
              />

              <div className="flex flex-col gap-6">
                <RequirementsList
                  title="Outstanding requirements"
                  caption="Track what Prep is automating with your city partners."
                  requirements={city.requirements}
                />
                <div className="flex flex-wrap gap-3" aria-label={`${city.displayName} permits`}>
                  {city.permits.length === 0 ? (
                    <span className="rounded-full border border-dashed border-border/60 px-4 py-2 text-xs uppercase tracking-wide text-muted-ink">
                      No permits on file
                    </span>
                  ) : (
                    city.permits.map((permit) => (
                      <PermitBadge key={`${city.slug}-${permit.permitNumber ?? permit.name}`} {...permit} />
                    ))
                  )}
                </div>
              </div>
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
