import { cn } from '@/lib/utils';
import type { HTMLAttributes } from 'react';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'text' | 'circular' | 'rectangular';
  shimmer?: boolean;
}

export const Skeleton = ({
  className,
  variant = 'default',
  shimmer = true,
  ...props
}: SkeletonProps) => {
  const variantClasses = {
    default: 'rounded-lg',
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: 'rounded-md'
  };

  return (
    <div
      className={cn(
        'relative overflow-hidden bg-border/40',
        variantClasses[variant],
        !shimmer && 'animate-pulse',
        className
      )}
      aria-hidden="true"
      {...props}
    >
      {shimmer && (
        <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      )}
    </div>
  );
};

// Convenience components for common skeleton patterns
export const SkeletonText = ({ className, lines = 1 }: { className?: string; lines?: number }) => (
  <div className={cn('space-y-2', className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} variant="text" className={cn(i === lines - 1 && lines > 1 && 'w-4/5')} />
    ))}
  </div>
);

export const SkeletonCard = ({ className }: { className?: string }) => (
  <div className={cn('space-y-4 rounded-2xl border border-border bg-surface p-6', className)}>
    <div className="flex items-center space-x-4">
      <Skeleton variant="circular" className="h-12 w-12" />
      <div className="flex-1 space-y-2">
        <Skeleton variant="text" className="w-3/4" />
        <Skeleton variant="text" className="w-1/2" />
      </div>
    </div>
    <SkeletonText lines={3} />
  </div>
);

export const SkeletonTable = ({ rows = 5, className }: { rows?: number; className?: string }) => (
  <div className={cn('space-y-3', className)}>
    <div className="flex gap-4">
      <Skeleton className="h-10 flex-1" />
      <Skeleton className="h-10 flex-1" />
      <Skeleton className="h-10 flex-1" />
    </div>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex gap-4">
        <Skeleton className="h-12 flex-1" />
        <Skeleton className="h-12 flex-1" />
        <Skeleton className="h-12 flex-1" />
      </div>
    ))}
  </div>
);

export const SkeletonAvatar = ({
  size = 'md',
  className
}: {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) => {
  const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-12 w-12',
    lg: 'h-16 w-16'
  };

  return <Skeleton variant="circular" className={cn(sizeClasses[size], className)} />;
};
