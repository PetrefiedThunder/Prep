import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export type PermitStatus = 'active' | 'expiring' | 'expired';

export interface PermitBadgeProps {
  name: string;
  status: PermitStatus;
  permitNumber?: string;
  expiresOn?: string;
  issuedBy?: string;
}

const statusStyles: Record<PermitStatus, string> = {
  active: 'border-emerald-300 bg-emerald-100/80 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-100',
  expiring: 'border-amber-300 bg-amber-100/80 text-amber-900 dark:border-amber-700 dark:bg-amber-900/40 dark:text-amber-100',
  expired: 'border-rose-300 bg-rose-100/80 text-rose-900 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-100'
};

const statusLabels: Record<PermitStatus, string> = {
  active: 'Active permit',
  expiring: 'Expiring soon',
  expired: 'Expired'
};

const formatExpiry = (value?: string) => {
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

export const PermitBadge = ({ name, status, permitNumber, expiresOn, issuedBy }: PermitBadgeProps) => {
  const expiry = formatExpiry(expiresOn);
  return (
    <Badge className={cn('inline-flex min-w-[14rem] flex-col items-start gap-1 rounded-2xl px-4 py-3 text-left text-xs shadow-sm', statusStyles[status])}>
      <span className="text-[11px] font-semibold uppercase tracking-wide">{statusLabels[status]}</span>
      <span className="text-sm font-semibold">{name}</span>
      {issuedBy ? <span className="text-[11px] text-muted-ink/90">Issued by {issuedBy}</span> : null}
      {permitNumber ? <span className="text-[11px] text-muted-ink/90">Permit #{permitNumber}</span> : null}
      {expiry ? <span className="text-[11px] text-muted-ink/90">Expires {expiry}</span> : null}
    </Badge>
  );
};

PermitBadge.displayName = 'PermitBadge';
