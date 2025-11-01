import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency } from '@/lib/currency';

export type FeeFrequency = 'one_time' | 'annual' | 'semiannual' | 'quarterly' | 'monthly';

export interface FeeLineItem {
  id: string;
  name: string;
  amount: number;
  frequency?: FeeFrequency;
  due?: string;
  description?: string;
}

export interface FeeCardProps {
  city: string;
  state: string;
  updatedAt?: string;
  summary?: string;
  fees: FeeLineItem[];
  currency?: string;
}

const frequencyLabels: Record<FeeFrequency, string> = {
  one_time: 'One-time',
  annual: 'Annual',
  semiannual: 'Semiannual',
  quarterly: 'Quarterly',
  monthly: 'Monthly'
};

const formatDueDate = (value?: string) => {
  if (!value) return null;
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return `Due every ${numeric} days`;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `Due ${date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })}`;
};

export const FeeCard = ({ city, state, updatedAt, summary, fees, currency = 'USD' }: FeeCardProps) => (
  <Card className="h-full">
    <CardHeader>
      <CardTitle className="flex items-center justify-between text-xl">
        <span>{city}, {state}</span>
        {updatedAt ? (
          <span className="text-xs font-normal uppercase tracking-wide text-muted-ink">
            Updated {new Date(updatedAt).toLocaleDateString()}
          </span>
        ) : null}
      </CardTitle>
      {summary ? <CardDescription>{summary}</CardDescription> : null}
    </CardHeader>
    <CardContent>
      {fees.length === 0 ? (
        <p className="text-sm text-muted-ink">No fee records available.</p>
      ) : (
        <ul className="flex flex-col gap-4" aria-label={`Fee breakdown for ${city}, ${state}`}>
          {fees.map((fee) => {
            const dueLabel = formatDueDate(fee.due);
            return (
              <li
                key={fee.id}
                className="flex items-start justify-between gap-4 rounded-2xl border border-border/60 bg-white/50 p-4 shadow-sm backdrop-blur dark:bg-surface/50"
              >
                <div className="flex-1">
                  <p className="text-sm font-semibold text-ink">{fee.name}</p>
                  {fee.description ? (
                    <p className="mt-1 text-xs text-muted-ink">{fee.description}</p>
                  ) : null}
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-ink">{formatCurrency(fee.amount, currency)}</p>
                  <div className="mt-1 flex flex-col text-xs text-muted-ink">
                    {fee.frequency ? (
                      <span>{frequencyLabels[fee.frequency] ?? fee.frequency}</span>
                    ) : null}
                    {dueLabel ? <span>{dueLabel}</span> : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </CardContent>
  </Card>
);

FeeCard.displayName = 'FeeCard';
