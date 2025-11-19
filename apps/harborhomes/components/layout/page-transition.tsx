'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { usePathname } from 'next/navigation';
import { pageTransition } from '@/lib/animations';
import type { ReactNode } from 'react';

export interface PageTransitionProps {
  children: ReactNode;
  className?: string;
  disableAnimation?: boolean;
}

/**
 * PageTransition Component
 *
 * Wraps page content with smooth fade-in transitions.
 * Automatically triggers on route changes.
 *
 * Usage:
 * ```tsx
 * <PageTransition>
 *   <YourPageContent />
 * </PageTransition>
 * ```
 */
export const PageTransition = ({
  children,
  className,
  disableAnimation = false
}: PageTransitionProps) => {
  const pathname = usePathname();

  if (disableAnimation) {
    return <div className={className}>{children}</div>;
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        className={className}
        initial="initial"
        animate="animate"
        exit="exit"
        variants={pageTransition}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};

/**
 * FadeIn Component
 *
 * Simple fade-in wrapper for individual elements
 */
export const FadeIn = ({
  children,
  className,
  delay = 0
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) => {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25, delay }}
    >
      {children}
    </motion.div>
  );
};

/**
 * SlideIn Component
 *
 * Slide in from specified direction
 */
export const SlideIn = ({
  children,
  className,
  direction = 'up',
  delay = 0
}: {
  children: ReactNode;
  className?: string;
  direction?: 'up' | 'down' | 'left' | 'right';
  delay?: number;
}) => {
  const directionMap = {
    up: { y: 20 },
    down: { y: -20 },
    left: { x: 20 },
    right: { x: -20 }
  };

  return (
    <motion.div
      className={className}
      initial={{ ...directionMap[direction], opacity: 0 }}
      animate={{ x: 0, y: 0, opacity: 1 }}
      transition={{
        duration: 0.35,
        delay,
        ease: [0, 0, 0.2, 1]
      }}
    >
      {children}
    </motion.div>
  );
};
