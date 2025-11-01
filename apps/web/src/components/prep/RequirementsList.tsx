import { friendlyRequirementStatus } from '../../lib/prepTypes';
import type { RequirementsParty } from '../../lib/prepTypes';

export interface RequirementsListProps {
  parties: RequirementsParty[];
  changeCandidates?: { id: string; title: string; summary: string }[];
}

export function RequirementsList({ parties, changeCandidates }: RequirementsListProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-lg font-semibold text-slate-900">Requirements</h2>
        <p className="text-sm text-slate-500">What operators and platform teams must complete</p>
      </header>
      <div className="space-y-6 px-4 py-6">
        {parties.map((party) => (
          <div key={party.party} className="space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{party.label}</h3>
              <p className="text-xs text-slate-500">{party.requirements.length} tracked items</p>
            </div>
            <ul className="space-y-2">
              {party.requirements.map((req) => (
                <li
                  key={req.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
                >
                  <div className="flex flex-col gap-1 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{req.title}</p>
                      {req.description && <p className="text-xs text-slate-600">{req.description}</p>}
                      {req.documentation_url && (
                        <a
                          href={req.documentation_url}
                          className="text-xs font-medium text-indigo-600 underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          View guidance
                        </a>
                      )}
                    </div>
                    <div className="text-right">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${badgeClassName(req.status, req.blocking)}`}
                      >
                        {friendlyRequirementStatus(req.status)}
                        {req.blocking ? ' • Blocking' : ''}
                      </span>
                      {req.due_date && (
                        <p className="text-xs text-slate-500">Due {new Date(req.due_date).toLocaleDateString()}</p>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {changeCandidates && changeCandidates.length > 0 && (
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
            <p className="font-semibold">Change candidates</p>
            <ul className="list-disc space-y-1 pl-5">
              {changeCandidates.map((candidate) => (
                <li key={candidate.id}>
                  <span className="font-medium">{candidate.title}:</span> {candidate.summary}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function badgeClassName(status: string, blocking?: boolean) {
  if (status === 'met') {
    return 'bg-emerald-100 text-emerald-800';
  }

  if (status === 'blocked' || blocking) {
    return 'bg-rose-100 text-rose-800';
  }

  return 'bg-amber-100 text-amber-800';
}

export default RequirementsList;
