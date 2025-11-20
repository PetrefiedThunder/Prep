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
        <div className="hidden items-center gap-6 lg:flex">
          <Link
            href={`${localePrefix}/dashboard`}
            className={`text-sm font-medium transition-colors ${pathname.includes('/dashboard') ? 'text-brand' : 'text-ink hover:text-brand'}`}
          >
            Dashboard
          </Link>
          <Link
            href={`${localePrefix}/vendors`}
            className={`text-sm font-medium transition-colors ${pathname.includes('/vendors') ? 'text-brand' : 'text-ink hover:text-brand'}`}
          >
            Vendors
          </Link>
          <Link
            href={`${localePrefix}/documents`}
            className={`text-sm font-medium transition-colors ${pathname.includes('/documents') ? 'text-brand' : 'text-ink hover:text-brand'}`}
          >
            Documents
          </Link>

          <div className="flex items-center gap-2 ml-2 pl-2 border-l border-border">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="focus-ring flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-2 text-sm hover:bg-surface-elevated transition-colors">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brand/10 text-sm font-semibold text-brand">
                    <UserRound className="h-4 w-4" />
                  </div>
                  <span className="text-sm font-medium">Admin</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link href={`${localePrefix}/account`}>Account Settings</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href={`${localePrefix}/auth/sign-in`}>Sign Out</Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <ThemeToggle />
          </div>
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
                <Link
                  href={`${localePrefix}/dashboard`}
                  className={`font-medium transition-colors ${pathname.includes('/dashboard') ? 'text-brand' : 'text-ink hover:text-brand'}`}
                  onClick={() => setMobileOpen(false)}
                >
                  Dashboard
                </Link>
                <Link
                  href={`${localePrefix}/vendors`}
                  className={`font-medium transition-colors ${pathname.includes('/vendors') ? 'text-brand' : 'text-ink hover:text-brand'}`}
                  onClick={() => setMobileOpen(false)}
                >
                  Vendors
                </Link>
                <Link
                  href={`${localePrefix}/documents`}
                  className={`font-medium transition-colors ${pathname.includes('/documents') ? 'text-brand' : 'text-ink hover:text-brand'}`}
                  onClick={() => setMobileOpen(false)}
                >
                  Documents
                </Link>
                <div className="my-2 border-t border-border" />
                <Link href={`${localePrefix}/account`} className="text-ink-muted hover:text-brand" onClick={() => setMobileOpen(false)}>
                  Account Settings
                </Link>
                <Link href={`${localePrefix}/auth/sign-in`} className="text-ink-muted hover:text-brand" onClick={() => setMobileOpen(false)}>
                  Sign Out
                </Link>
              </nav>
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
