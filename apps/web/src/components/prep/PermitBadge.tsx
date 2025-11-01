import type { PermitStatus } from '../../lib/prepTypes';

export interface PermitBadgeProps {
  cityLabel: string;
  status: PermitStatus;
  blockingCount?: number;
  lastUpdated?: string;
}

const STATUS_STYLES: Record<PermitStatus, string> = {
  ready: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
  in_progress: 'bg-amber-100 text-amber-800 border border-amber-200',
  blocked: 'bg-rose-100 text-rose-800 border border-rose-200',
};

const STATUS_LABELS: Record<PermitStatus, string> = {
  ready: 'Ready for launch',
  in_progress: 'In progress',
  blocked: 'Action required',
};

export function PermitBadge({ cityLabel, status, blockingCount, lastUpdated }: PermitBadgeProps) {
  return (
    <div className={`rounded-full px-4 py-2 text-sm font-semibold flex items-center gap-2 ${STATUS_STYLES[status]}`}>
      <span className="inline-flex h-2 w-2 rounded-full bg-current" aria-hidden="true" />
      <span>{cityLabel}</span>
      <span aria-live="polite">{STATUS_LABELS[status]}</span>
      {typeof blockingCount === 'number' && (
        <span className="text-xs font-normal text-slate-600">{blockingCount} blocking</span>
      )}
      {lastUpdated && (
        <span className="text-xs font-normal text-slate-500">Updated {new Date(lastUpdated).toLocaleDateString()}</span>
      )}
    </div>
  );
}

export default PermitBadge;
