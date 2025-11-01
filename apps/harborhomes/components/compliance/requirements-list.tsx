import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export type RequirementStatus = 'met' | 'pending' | 'overdue';

export interface RequirementItem {
  id: string;
  title: string;
  status: RequirementStatus;
  detail?: string;
  due?: string;
}

export interface RequirementsListProps {
  title?: string;
  caption?: string;
  requirements: RequirementItem[];
}

const statusStyles: Record<RequirementStatus, string> = {
  met: 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-900/30 dark:text-emerald-200',
  pending: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800/60 dark:bg-amber-900/30 dark:text-amber-200',
  overdue: 'border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-800/60 dark:bg-rose-900/30 dark:text-rose-200'
};

const statusLabels: Record<RequirementStatus, string> = {
  met: 'Met',
  pending: 'In progress',
  overdue: 'Overdue'
};

const formatDueDate = (value?: string) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

export const RequirementsList = ({ title = 'Regulatory requirements', caption, requirements }: RequirementsListProps) => (
  <section aria-label={title} className="flex flex-col gap-4 rounded-3xl border border-border/60 bg-white/70 p-6 shadow-sm backdrop-blur dark:bg-surface/60">
    <header>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {caption ? <p className="mt-1 text-sm text-muted-ink">{caption}</p> : null}
    </header>
    {requirements.length === 0 ? (
      <p className="rounded-2xl border border-dashed border-border/60 bg-white/60 p-4 text-sm text-muted-ink dark:bg-surface/40">
        All requirements are satisfied.
      </p>
    ) : (
      <ul className="flex flex-col gap-3">
        {requirements.map((item) => {
          const due = formatDueDate(item.due);
          return (
            <li key={item.id} className="flex items-start justify-between gap-4 rounded-2xl border border-border/60 bg-white/80 p-4 shadow-sm dark:bg-surface/40">
              <div className="flex-1">
                <p className="text-sm font-medium text-ink">{item.title}</p>
                {item.detail ? <p className="mt-1 text-xs text-muted-ink">{item.detail}</p> : null}
                {due ? <p className="mt-1 text-xs text-muted-ink">Due {due}</p> : null}
              </div>
              <Badge className={cn('whitespace-nowrap text-[11px] font-semibold uppercase tracking-wide', statusStyles[item.status])}>
                {statusLabels[item.status]}
              </Badge>
            </li>
          );
        })}
      </ul>
    )}
  </section>
);

RequirementsList.displayName = 'RequirementsList';
