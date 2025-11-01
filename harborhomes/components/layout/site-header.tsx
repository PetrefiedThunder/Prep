"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion, useScroll, useTransform } from "framer-motion";
import { Globe2, Heart, Menu, MessageCircle, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { SearchPill } from "@/components/search/search-pill";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useTranslations } from "next-intl";

export function SiteHeader() {
  const { scrollY } = useScroll();
  const opacity = useTransform(scrollY, [0, 120], [0, 1]);
  const pathname = usePathname();
  const t = useTranslations("nav");

  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <motion.header
      className="sticky top-0 z-40 w-full bg-white/80 backdrop-blur-xl"
      style={{ boxShadow: opacity.to((value) => `0 1px 0 rgba(15,23,42,${value * 0.08})`) }}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
          <span className="rounded-full bg-brand px-3 py-1 text-sm font-semibold uppercase text-brand-contrast">Harbor</span>
          <span>Homes</span>
        </Link>
        <div className="hidden flex-1 items-center justify-center md:flex">
          <SearchPill />
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <Link href="/demo/sf-and-jt" className="text-sm font-medium text-muted-ink transition hover:text-ink">
            {t("complianceDemo")}
          </Link>
          <Button variant="ghost" className="text-sm" asChild>
            <Link href="/host">{t("becomeHost")}</Link>
          </Button>
          <LanguageSwitcher />
          <ThemeToggle />
          <AccountMenu />
        </div>
        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open navigation">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full max-w-xs">
              <nav className="flex flex-col gap-4 pt-10">
                <SearchPill variant="stacked" onAction={() => setOpen(false)} />
                <Link href="/wishlists" className="text-sm font-medium" onClick={() => setOpen(false)}>
                  <Heart className="mr-2 inline h-4 w-4" /> {t("wishlists")}
                </Link>
                <Link href="/trips" className="text-sm font-medium" onClick={() => setOpen(false)}>
                  <Globe2 className="mr-2 inline h-4 w-4" /> {t("trips")}
                </Link>
                <Link href="/demo/sf-and-jt" className="text-sm font-medium" onClick={() => setOpen(false)}>
                  {t("complianceDemo")}
                </Link>
                <Link href="/inbox" className="text-sm font-medium" onClick={() => setOpen(false)}>
                  <MessageCircle className="mr-2 inline h-4 w-4" /> {t("inbox")}
                </Link>
                <Link href="/host" className="text-sm font-medium" onClick={() => setOpen(false)}>
                  {t("becomeHost")}
                </Link>
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
      <div className="md:hidden">
        <div className="px-6 pb-4">
          <SearchPill />
        </div>
      </div>
    </motion.header>
  );
}

function LanguageSwitcher() {
  const router = useRouter();
  const params = useSearchParams();
  const pathname = usePathname();

  const changeLocale = (locale: string) => {
    const query = new URLSearchParams(params.toString());
    document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=${60 * 60 * 24 * 30}`;
    router.push(`${pathname}?${query.toString()}`);
    router.refresh();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Switch language">
          <Globe2 className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => changeLocale("en")}>English</DropdownMenuItem>
        <DropdownMenuItem onClick={() => changeLocale("es")}>Español</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function AccountMenu() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-2 rounded-full border border-border px-4 py-2">
          <Menu className="h-4 w-4" />
          <UserRound className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem asChild>
          <Link href="/auth/sign-up">Sign up</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/auth/sign-in">Log in</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/account">Account</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/wishlists">Wishlists</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/trips">Trips</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/inbox">Inbox</Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
