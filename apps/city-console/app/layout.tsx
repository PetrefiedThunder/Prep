import type { Metadata } from 'next';
import { ReactNode } from 'react';

import { Navigation } from '@/components/layout/navigation';

import './globals.css';

export const metadata: Metadata = {
  title: 'Prep City Console',
  description: 'City compliance console for monitoring policy decisions, fees, and required documentation.'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Navigation />
        <main>{children}</main>
      </body>
    </html>
  );
}
