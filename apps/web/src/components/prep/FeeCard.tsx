import { formatCurrency, friendlyFeeKind } from '../../lib/prepTypes';
import type { FeeItem, FeeTotals } from '../../lib/prepTypes';

export interface FeeCardProps {
  cityLabel: string;
  totals: FeeTotals;
  items: FeeItem[];
  currency: string;
  validationIssues?: string[];
  lastValidatedAt?: string;
}

export function FeeCard({ cityLabel, totals, items, currency, validationIssues, lastValidatedAt }: FeeCardProps) {
  const totalAmount =
    (totals.one_time ?? 0) + (totals.recurring ?? 0) + (totals.incremental ?? 0);

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-lg font-semibold text-slate-900">{cityLabel} fees</h2>
        <p className="text-sm text-slate-500">Validated financial obligations for launch</p>
      </header>
      <div className="space-y-4 px-4 py-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <FeeTotal label="One-time" amount={totals.one_time ?? 0} currency={currency} />
          <FeeTotal label="Recurring" amount={totals.recurring ?? 0} currency={currency} />
          <FeeTotal label="Incremental" amount={totals.incremental ?? 0} currency={currency} />
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Total exposure:</span>{' '}
          {formatCurrency(totalAmount, currency)}
          {lastValidatedAt && (
            <span className="ml-2 text-xs text-slate-500">
              Last validated {new Date(lastValidatedAt).toLocaleDateString()}
            </span>
          )}
        </div>
        {validationIssues && validationIssues.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <p className="font-semibold">Validation issues</p>
            <ul className="list-disc space-y-1 pl-5">
              {validationIssues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
        <ul className="divide-y divide-slate-200">
          {items.map((fee) => (
            <li key={fee.id} className="py-3">
              <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{fee.label}</p>
                  <p className="text-xs text-slate-500">
                    {friendlyFeeKind(fee.kind)}
                    {fee.cadence ? ` • ${fee.cadence}` : ''}
                    {fee.unit ? ` • ${fee.unit}` : ''}
                  </p>
                  {fee.description && <p className="text-xs text-slate-600">{fee.description}</p>}
                </div>
                <p className="text-sm font-semibold text-slate-900">
                  {formatCurrency(fee.amount, fee.currency)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

interface FeeTotalProps {
  label: string;
  amount: number;
  currency: string;
}

function FeeTotal({ label, amount, currency }: FeeTotalProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900">
        {formatCurrency(amount, currency)}
      </p>
    </div>
  );
}

export default FeeCard;
