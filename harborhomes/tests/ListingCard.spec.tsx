import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { ListingCard } from "@/components/listings/listing-card";
import { listings } from "@/lib/mock-data";

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children }: { children: ReactNode }) => <a>{children}</a>
}));

it("renders listing title", () => {
  render(<ListingCard listing={listings[0]} />);
  expect(screen.getByText(listings[0].title)).toBeInTheDocument();
});
