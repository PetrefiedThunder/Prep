'use client';

import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, MotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { ButtonHTMLAttributes } from 'react';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-full border border-transparent bg-brand px-4 py-2 text-sm font-medium transition-colors duration-base focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-brand disabled:cursor-not-allowed disabled:opacity-60',
  {
    variants: {
      variant: {
        primary: 'bg-brand text-white shadow-sm hover:bg-brand-600',
        secondary: 'bg-surface text-ink border border-border hover:bg-surface-elevated shadow-sm',
        ghost: 'bg-transparent text-ink hover:bg-surface',
        outline: 'border border-border bg-transparent text-ink hover:bg-surface',
        destructive: 'bg-error text-white shadow-sm hover:bg-error-dark'
      },
      size: {
        sm: 'px-3 py-1.5 text-xs',
        md: 'px-4 py-2 text-sm',
        lg: 'px-6 py-3 text-base'
      }
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md'
    }
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  disableAnimation?: boolean;
}

const MotionButton = motion.button;

export const Button = ({
  className,
  variant,
  size,
  asChild,
  disableAnimation = false,
  disabled,
  ...props
}: ButtonProps) => {
  const baseClassName = cn(buttonVariants({ variant, size }), className);

  if (asChild) {
    return <Slot className={baseClassName} {...props} />;
  }

  if (disableAnimation || disabled) {
    return <button className={baseClassName} disabled={disabled} {...props} />;
  }

  // Animation props for interactive states
  const motionProps: MotionProps = {
    whileHover: { scale: 1.02 },
    whileTap: { scale: 0.98 },
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 30
    }
  };

  return (
    <MotionButton
      className={baseClassName}
      disabled={disabled}
      {...motionProps}
      {...props}
    />
  );
};

export { buttonVariants };
