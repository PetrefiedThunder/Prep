import '@/styles/globals.css';
import { NextIntlClientProvider } from 'next-intl';
import { notFound } from 'next/navigation';
import { ReactNode } from 'react';
import { SiteHeader } from '@/components/layout/site-header';
import { Toaster } from '@/components/ui';
import { locales, getMessages } from '@/lib/i18n';

export const metadata = {
  title: 'HarborHomes – Curated stays for curious travelers',
  description: 'Discover welcoming homes and boutique retreats with HarborHomes.'
};

export default async function LocaleLayout({
  children,
  params: { locale }
}: {
  children: ReactNode;
  params: { locale: string };
}) {
  if (!locales.includes(locale as any)) {
    notFound();
  }

  const messages = getMessages(locale);

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className="min-h-screen bg-[hsl(var(--bg))] text-[hsl(var(--ink))]">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <SiteHeader />
          <main className="mx-auto min-h-[80vh] max-w-7xl px-4 pb-16 pt-10">{children}</main>
          <Toaster />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
