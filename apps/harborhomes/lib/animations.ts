/**
 * PrepChef Animation Primitives
 *
 * Reusable Framer Motion variants for consistent, smooth animations across the app.
 * All animations respect prefers-reduced-motion for accessibility.
 */

import type { Variants, Transition } from 'framer-motion';

// ============================================================================
// Easing Functions
// ============================================================================

export const EASING = {
  smoothIn: [0.4, 0, 1, 1] as const,
  smoothOut: [0, 0, 0.2, 1] as const,
  smoothInOut: [0.4, 0, 0.2, 1] as const,
  spring: [0.34, 1.56, 0.64, 1] as const,
  bounce: [0.68, -0.55, 0.265, 1.55] as const
};

// ============================================================================
// Duration Constants
// ============================================================================

export const DURATION = {
  fast: 0.15,
  base: 0.25,
  slow: 0.35,
  slower: 0.5
} as const;

// ============================================================================
// Default Transitions
// ============================================================================

export const TRANSITIONS = {
  fast: { duration: DURATION.fast, ease: EASING.smoothOut } as Transition,
  base: { duration: DURATION.base, ease: EASING.smoothInOut } as Transition,
  slow: { duration: DURATION.slow, ease: EASING.smoothInOut } as Transition,
  spring: { type: 'spring', stiffness: 300, damping: 30 } as Transition,
  bounce: { type: 'spring', stiffness: 400, damping: 15 } as Transition
};

// ============================================================================
// Fade Animations
// ============================================================================

export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: TRANSITIONS.base },
  exit: { opacity: 0, transition: TRANSITIONS.fast }
};

export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: TRANSITIONS.base },
  exit: { opacity: 0, y: 10, transition: TRANSITIONS.fast }
};

export const fadeInDown: Variants = {
  initial: { opacity: 0, y: -10 },
  animate: { opacity: 1, y: 0, transition: TRANSITIONS.base },
  exit: { opacity: 0, y: -10, transition: TRANSITIONS.fast }
};

// ============================================================================
// Slide Animations
// ============================================================================

export const slideInUp: Variants = {
  initial: { y: 20, opacity: 0 },
  animate: { y: 0, opacity: 1, transition: TRANSITIONS.slow },
  exit: { y: 20, opacity: 0, transition: TRANSITIONS.fast }
};

export const slideInDown: Variants = {
  initial: { y: -20, opacity: 0 },
  animate: { y: 0, opacity: 1, transition: TRANSITIONS.slow },
  exit: { y: -20, opacity: 0, transition: TRANSITIONS.fast }
};

export const slideInRight: Variants = {
  initial: { x: -20, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: TRANSITIONS.slow },
  exit: { x: -20, opacity: 0, transition: TRANSITIONS.fast }
};

export const slideInLeft: Variants = {
  initial: { x: 20, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: TRANSITIONS.slow },
  exit: { x: 20, opacity: 0, transition: TRANSITIONS.fast }
};

// ============================================================================
// Scale Animations
// ============================================================================

export const scaleIn: Variants = {
  initial: { scale: 0.95, opacity: 0 },
  animate: { scale: 1, opacity: 1, transition: TRANSITIONS.base },
  exit: { scale: 0.95, opacity: 0, transition: TRANSITIONS.fast }
};

export const scaleInBounce: Variants = {
  initial: { scale: 0.8, opacity: 0 },
  animate: { scale: 1, opacity: 1, transition: TRANSITIONS.bounce },
  exit: { scale: 0.8, opacity: 0, transition: TRANSITIONS.fast }
};

export const scaleInSpring: Variants = {
  initial: { scale: 0.9, opacity: 0 },
  animate: { scale: 1, opacity: 1, transition: TRANSITIONS.spring },
  exit: { scale: 0.9, opacity: 0, transition: TRANSITIONS.fast }
};

// ============================================================================
// Stagger Animations (for lists and grids)
// ============================================================================

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1
    }
  },
  exit: {
    transition: {
      staggerChildren: 0.03,
      staggerDirection: -1
    }
  }
};

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: TRANSITIONS.base },
  exit: { opacity: 0, y: 10, transition: TRANSITIONS.fast }
};

// ============================================================================
// Dialog/Modal Animations
// ============================================================================

export const dialogOverlay: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: DURATION.base } },
  exit: { opacity: 0, transition: { duration: DURATION.fast } }
};

export const dialogContent: Variants = {
  initial: { scale: 0.95, opacity: 0, y: 10 },
  animate: { scale: 1, opacity: 1, y: 0, transition: TRANSITIONS.spring },
  exit: { scale: 0.95, opacity: 0, y: 10, transition: TRANSITIONS.fast }
};

// ============================================================================
// Card Hover Animations
// ============================================================================

export const cardHover = {
  rest: {
    scale: 1,
    y: 0,
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)'
  },
  hover: {
    scale: 1.02,
    y: -4,
    boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    transition: TRANSITIONS.fast
  }
};

export const cardHoverSubtle = {
  rest: {
    scale: 1,
    y: 0
  },
  hover: {
    scale: 1.01,
    y: -2,
    transition: TRANSITIONS.fast
  }
};

// ============================================================================
// Button Animations
// ============================================================================

export const buttonTap = {
  scale: 0.97,
  transition: { duration: 0.1 }
};

export const buttonHover = {
  scale: 1.02,
  transition: TRANSITIONS.fast
};

// ============================================================================
// Notification/Toast Animations
// ============================================================================

export const toastSlideIn: Variants = {
  initial: { x: 400, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: TRANSITIONS.spring },
  exit: { x: 400, opacity: 0, transition: TRANSITIONS.fast }
};

// ============================================================================
// Page Transition Animations
// ============================================================================

export const pageTransition: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: DURATION.slow,
      ease: EASING.smoothOut,
      when: 'beforeChildren'
    }
  },
  exit: {
    opacity: 0,
    y: 20,
    transition: {
      duration: DURATION.fast,
      ease: EASING.smoothIn
    }
  }
};

// ============================================================================
// Loading Animations
// ============================================================================

export const pulse: Variants = {
  initial: { opacity: 0.5 },
  animate: {
    opacity: 1,
    transition: {
      duration: 1,
      repeat: Infinity,
      repeatType: 'reverse',
      ease: 'easeInOut'
    }
  }
};

export const spin: Variants = {
  animate: {
    rotate: 360,
    transition: {
      duration: 1,
      repeat: Infinity,
      ease: 'linear'
    }
  }
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Creates a custom stagger container with configurable stagger delay
 */
export const createStaggerContainer = (staggerDelay = 0.05): Variants => ({
  initial: {},
  animate: {
    transition: {
      staggerChildren: staggerDelay,
      delayChildren: 0.1
    }
  },
  exit: {
    transition: {
      staggerChildren: staggerDelay / 2,
      staggerDirection: -1
    }
  }
});

/**
 * Creates a delayed fade-in animation
 */
export const createDelayedFadeIn = (delay = 0): Variants => ({
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { ...TRANSITIONS.base, delay } },
  exit: { opacity: 0, transition: TRANSITIONS.fast }
});

/**
 * Creates a custom slide-in animation with configurable distance and direction
 */
export const createSlideIn = (distance = 20, direction: 'up' | 'down' | 'left' | 'right' = 'up'): Variants => {
  const axis = direction === 'left' || direction === 'right' ? 'x' : 'y';
  const value = direction === 'up' || direction === 'left' ? distance : -distance;

  return {
    initial: { [axis]: value, opacity: 0 },
    animate: { [axis]: 0, opacity: 1, transition: TRANSITIONS.slow },
    exit: { [axis]: value, opacity: 0, transition: TRANSITIONS.fast }
  };
};
