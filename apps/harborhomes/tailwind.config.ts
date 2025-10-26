import type { Config } from 'tailwindcss';
import animate from 'tailwindcss-animate';
import typography from '@tailwindcss/typography';

const config: Config = {
  darkMode: ['class', '[data-theme="dark"]'],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'ui-sans-serif']
      },
      colors: {
        brand: 'hsl(11 85% 54%)',
        'brand-contrast': 'hsl(0 0% 100%)',
        ink: 'hsl(222 47% 11%)',
        'muted-ink': 'hsl(222 20% 35%)',
        surface: 'hsl(210 20% 98%)',
        border: 'hsl(214 20% 89%)'
      },
      borderRadius: {
        xl: '1.5rem'
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' }
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out'
      }
    }
  },
  plugins: [animate, typography]
};

export default config;
