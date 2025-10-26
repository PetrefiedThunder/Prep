import { cn } from '@/lib/utils';

export const Skeleton = ({ className }: { className?: string }) => (
  <div className={cn('animate-pulse rounded-2xl bg-border/60', className)} aria-hidden="true" />
);
