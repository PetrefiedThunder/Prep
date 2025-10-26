import { render, screen } from "@testing-library/react";
import { BookingCard } from "@/components/listings/booking-card";
import { listings } from "@/lib/mock-data";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() })
}));

Object.defineProperty(window, "location", {
  value: { href: "" },
  writable: true
});

it("shows nightly price", () => {
  render(<BookingCard listing={listings[0]} />);
  expect(screen.getByText(/per night/i)).toBeInTheDocument();
});
