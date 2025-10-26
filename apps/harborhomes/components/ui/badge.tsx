import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export const Badge = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      'inline-flex items-center rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium uppercase tracking-wide text-muted-ink',
      className
    )}
    {...props}
  />
);
