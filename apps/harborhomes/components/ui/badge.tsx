import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import type { HTMLAttributes } from 'react';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-border bg-surface text-ink hover:bg-surface-sunken',
        success: 'border-success/20 bg-success-light text-success-dark hover:bg-success-light/80',
        warning: 'border-warning/20 bg-warning-light text-warning-dark hover:bg-warning-light/80',
        error: 'border-error/20 bg-error-light text-error-dark hover:bg-error-light/80',
        info: 'border-info/20 bg-info-light text-info-dark hover:bg-info-light/80',
        brand: 'border-brand/20 bg-brand/10 text-brand hover:bg-brand/20',
        outline: 'border-border bg-transparent text-ink hover:bg-surface'
      },
      size: {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2.5 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'md'
    }
  }
);

export interface BadgeProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export const Badge = ({ className, variant, size, ...props }: BadgeProps) => (
  <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
);

export { badgeVariants };
