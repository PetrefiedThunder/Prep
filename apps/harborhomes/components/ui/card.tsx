'use client';

import { cn } from '@/lib/utils';
import { motion, type MotionProps } from 'framer-motion';
import type { HTMLAttributes } from 'react';

const MotionDiv = motion.div;

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  disableAnimation?: boolean;
}

export const Card = ({
  className,
  hoverable = false,
  disableAnimation = false,
  ...props
}: CardProps) => {
  const baseClassName = cn(
    'rounded-2xl border border-border bg-surface p-6 shadow-sm transition-shadow duration-base',
    className
  );

  if (disableAnimation || !hoverable) {
    return <div className={baseClassName} {...props} />;
  }

  // Smooth hover animation for interactive cards
  const motionProps: MotionProps = {
    whileHover: {
      y: -4,
      scale: 1.01,
      boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)'
    },
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30
    }
  };

  return <MotionDiv className={baseClassName} {...motionProps} {...props} />;
};

export const CardHeader = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('mb-4 flex flex-col gap-1', className)} {...props} />
);

export const CardTitle = ({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn('text-lg font-semibold text-ink', className)} {...props} />
);

export const CardDescription = ({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn('text-sm text-ink-muted', className)} {...props} />
);

export const CardContent = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex flex-col gap-4', className)} {...props} />
);

export const CardFooter = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('mt-4 flex items-center gap-2', className)} {...props} />
);
