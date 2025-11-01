import { useMemo } from 'react';
import { useCityCompliance } from '../hooks/useCityCompliance';
import type { CityKey } from '../hooks/useCityCompliance';
import { FeeCard, PermitBadge, RequirementsList } from '../components/prep';

const CITY_CONFIG: Record<CityKey, { label: string }> = {
  'san-francisco': { label: 'San Francisco, CA' },
  'joshua-tree': { label: 'Joshua Tree, CA' },
};

export default function SFJoshuaTreeDemo() {
  const sf = useCityCompliance('san-francisco');
  const jt = useCityCompliance('joshua-tree');

  const cities = useMemo(
    () => [
      { key: 'san-francisco' as CityKey, label: CITY_CONFIG['san-francisco'].label, state: sf },
      { key: 'joshua-tree' as CityKey, label: CITY_CONFIG['joshua-tree'].label, state: jt },
    ],
    [sf, jt],
  );

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-8">
      <header className="space-y-4 text-center">
        <h1 className="text-3xl font-bold text-slate-900">City readiness pilots</h1>
        <p className="text-base text-slate-600">
          Live compliance snapshots for San Francisco and Joshua Tree. Each section pulls from the
          same API surface your partners use.
        </p>
      </header>

      <div className="grid gap-8">
        {cities.map(({ key, label, state }) => (
          <section key={key} className="space-y-6 rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <h2 className="text-2xl font-semibold text-slate-900">{label}</h2>
              <PermitBadge
                cityLabel={label}
                status={state.status}
                blockingCount={state.data?.requirements.blocking_count}
                lastUpdated={state.data?.requirements.last_updated_at}
              />
            </div>

            {state.loading && <p className="text-sm text-slate-500">Loading compliance data…</p>}
            {state.error && (
              <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                Unable to load data: {state.error}
              </p>
            )}

            {!state.loading && !state.error && state.data && (
              <div className="grid gap-6 md:grid-cols-2">
                <FeeCard
                  cityLabel={label}
                  currency={state.data.fees.currency}
                  totals={state.data.fees.totals}
                  items={state.data.fees.items}
                  validationIssues={state.data.fees.validation_issues}
                  lastValidatedAt={state.data.fees.last_validated_at}
                />
                <RequirementsList
                  parties={state.data.requirements.parties}
                  changeCandidates={state.data.requirements.change_candidates}
                />
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
