'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Globe, Menu, UserRound } from 'lucide-react';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, Sheet, SheetContent, SheetTrigger } from '@/components/ui';
import { SearchPill } from '@/components/search/search-pill';
import { ThemeToggle } from '@/components/theme-toggle';

export const SiteHeader = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const localeSegment = pathname.split('/')[1] || 'en';
  const localePrefix = `/${localeSegment}`;
  const t = useTranslations('nav');

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-[hsl(var(--bg))]/80 backdrop-blur supports-[backdrop-filter]:bg-[hsl(var(--bg))]/60">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-4 px-4">
        <Link href={localePrefix} className="flex items-center gap-2 font-display text-xl font-semibold text-ink">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand text-lg text-white font-bold">PC</span>
          PrepChef
        </Link>
        <div className="hidden lg:flex">
          <SearchPill />
        </div>
        <div className="hidden items-center gap-2 lg:flex">
          <Link href={`${localePrefix}/host`} className="text-sm font-medium text-ink hover:text-brand">
            {t('becomeHost')}
          </Link>
          <Button variant="ghost" className="h-10 w-10 rounded-full">
            <Globe className="h-4 w-4" />
            <span className="sr-only">Language</span>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="focus-ring flex items-center gap-3 rounded-full border border-border bg-white px-3 py-2 text-sm">
                <Menu className="h-4 w-4" />
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand/20 text-sm font-semibold text-brand">
                  <UserRound className="h-4 w-4" />
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem asChild>
                <Link href={`${localePrefix}/wishlists`}>{t('wishlists')}</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`${localePrefix}/trips`}>{t('trips')}</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`${localePrefix}/inbox`}>Inbox</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`${localePrefix}/account`}>Account</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`${localePrefix}/auth/sign-in`}>Sign in</Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <ThemeToggle />
        </div>
        <div className="flex items-center gap-3 lg:hidden">
          <ThemeToggle />
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <button className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-white">
                <Menu className="h-5 w-5" />
                <span className="sr-only">Menu</span>
              </button>
            </SheetTrigger>
            <SheetContent>
              <nav className="mt-10 flex flex-col gap-4 text-base">
                <Link href={`${localePrefix}/search`} className="hover:text-brand" onClick={() => setMobileOpen(false)}>
                  Search
                </Link>
                <Link href={`${localePrefix}/wishlists`} className="hover:text-brand" onClick={() => setMobileOpen(false)}>
                  {t('wishlists')}
                </Link>
                <Link href={`${localePrefix}/trips`} className="hover:text-brand" onClick={() => setMobileOpen(false)}>
                  {t('trips')}
                </Link>
                <Link href={`${localePrefix}/inbox`} className="hover:text-brand" onClick={() => setMobileOpen(false)}>
                  Inbox
                </Link>
                <Link href={`${localePrefix}/host`} className="hover:text-brand" onClick={() => setMobileOpen(false)}>
                  {t('becomeHost')}
                </Link>
                <Link href={`${localePrefix}/account`} className="hover:text-brand" onClick={() => setMobileOpen(false)}>
                  Account
                </Link>
              </nav>
              <div className="mt-auto flex flex-col gap-2 text-sm text-muted-ink">
                <span>Currently on {pathname}</span>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
      <div className="flex border-t border-border/60 lg:hidden">
        <SearchPill compact />
      </div>
    </header>
  );
};
