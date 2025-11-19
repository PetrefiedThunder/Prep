'use client';

import { motion } from 'framer-motion';
import { fadeInUp, staggerContainer, staggerItem } from '@/lib/animations';
import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

export interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  breadcrumbs?: ReactNode;
  className?: string;
  disableAnimation?: boolean;
}

/**
 * PageHeader Component
 *
 * Consistent header for all pages with title, description, and optional actions.
 * Includes smooth fade-in animations.
 *
 * Usage:
 * ```tsx
 * <PageHeader
 *   title="Vendor Verifications"
 *   description="Manage vendor compliance status"
 *   actions={<Button>Add Vendor</Button>}
 * />
 * ```
 */
export const PageHeader = ({
  title,
  description,
  actions,
  breadcrumbs,
  className,
  disableAnimation = false
}: PageHeaderProps) => {
  if (disableAnimation) {
    return (
      <div className={cn('mb-8 space-y-4', className)}>
        {breadcrumbs && <div className="text-sm text-ink-muted">{breadcrumbs}</div>}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight text-ink md:text-4xl">{title}</h1>
            {description && <p className="text-lg text-ink-muted">{description}</p>}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className={cn('mb-8 space-y-4', className)}
      initial="initial"
      animate="animate"
      variants={staggerContainer}
    >
      {breadcrumbs && (
        <motion.div variants={staggerItem} className="text-sm text-ink-muted">
          {breadcrumbs}
        </motion.div>
      )}

      <div className="flex items-start justify-between gap-4">
        <motion.div variants={staggerItem} className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-ink md:text-4xl">{title}</h1>
          {description && <p className="text-lg text-ink-muted">{description}</p>}
        </motion.div>

        {actions && (
          <motion.div variants={staggerItem} className="flex gap-2">
            {actions}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

/**
 * PageHeaderSkeleton Component
 *
 * Loading state for PageHeader
 */
export const PageHeaderSkeleton = ({ className }: { className?: string }) => {
  return (
    <div className={cn('mb-8 space-y-4', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="h-10 w-2/3 animate-pulse rounded-lg bg-border/40" />
          <div className="h-6 w-1/2 animate-pulse rounded-lg bg-border/40" />
        </div>
        <div className="h-10 w-32 animate-pulse rounded-lg bg-border/40" />
      </div>
    </div>
  );
};
