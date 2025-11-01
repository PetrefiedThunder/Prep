import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { SiteHeader } from "@/components/layout/site-header";

vi.mock("framer-motion", () => ({
  motion: {
    header: ({ children, ...props }: { children: ReactNode }) => <header {...props}>{children}</header>
  },
  useScroll: () => ({ scrollY: { on: vi.fn() } }),
  useTransform: () => ({ to: (fn: (value: number) => unknown) => fn(0) })
}));

vi.mock("@/components/search/search-pill", () => ({
  SearchPill: () => <div data-testid="search-pill" />
}));

vi.mock("@/components/theme/theme-toggle", () => ({
  ThemeToggle: () => <button type="button">theme</button>
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuItem: ({ children, ...props }: { children: ReactNode }) => <div {...props}>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: ReactNode }) => <div>{children}</div>
}));

vi.mock("@/components/ui/sheet", () => ({
  Sheet: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetTrigger: ({ children }: { children: ReactNode }) => <div>{children}</div>
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams()
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key
}));

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, href }: { children: ReactNode; href: string }) => <a href={href}>{children}</a>
}));

describe("SiteHeader", () => {
  it("links to the San Francisco and Joshua Tree overview", () => {
    render(<SiteHeader />);
    const link = screen.getAllByRole("link", { name: "sfAndJt" })[0];
    expect(link).toHaveAttribute("href", "/sf-and-jt");
  });
});
