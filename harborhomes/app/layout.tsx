import type { ReactNode } from "react";
import "@/styles/globals.css";
import { Providers } from "./providers";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import type { Metadata } from "next";
import { cn } from "@/lib/utils";
import Script from "next/script";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  metadataBase: new URL("https://harborhomes.example"),
  title: {
    default: "HarborHomes | Thoughtful stays, anchored in comfort",
    template: "%s | HarborHomes"
  },
  description:
    "HarborHomes is a short-stay marketplace offering curated stays with mindful service, flexible bookings, and host-first tools.",
  openGraph: {
    title: "HarborHomes",
    description: "Thoughtful stays, anchored in comfort.",
    url: "https://harborhomes.example",
    siteName: "HarborHomes",
    locale: "en_US",
    type: "website"
  },
  twitter: {
    card: "summary_large_image",
    title: "HarborHomes",
    description: "Discover your next HarborHomes stay."
  }
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={cn("min-h-screen bg-bg font-sans text-ink antialiased", inter.variable)}>
        <Providers>
          <NextIntlClientProvider locale={locale} messages={messages}>
            {children}
          </NextIntlClientProvider>
        </Providers>
        <Script id="analytics-placeholder" strategy="afterInteractive">{`window.harborhomesAnalytics = window.harborhomesAnalytics || [];`}</Script>
      </body>
    </html>
  );
}
