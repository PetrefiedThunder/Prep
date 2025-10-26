import '@/styles/globals.css';
import { ReactNode } from 'react';

export const metadata = {
  title: 'HarborHomes',
  description: 'Short-stay marketplace demo.'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
