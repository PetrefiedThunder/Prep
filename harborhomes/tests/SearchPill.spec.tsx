import { render, fireEvent, screen } from "@testing-library/react";
import { SearchPill } from "@/components/search/search-pill";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/search"
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key
}));

it("opens dialog when clicked", () => {
  render(<SearchPill />);
  fireEvent.click(screen.getByRole("button", { name: /open search/i }));
  expect(screen.getByText(/Plan your next stay/i)).toBeInTheDocument();
});
