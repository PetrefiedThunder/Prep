import { render, fireEvent, screen } from "@testing-library/react";
import { FiltersDialog } from "@/components/search/filters-dialog";

it("toggles amenities", () => {
  const toggle = vi.fn();
  render(
    <FiltersDialog
      priceRange={[100, 500]}
      onPriceChange={() => undefined}
      amenities={["EV charger"]}
      selectedAmenities={[]}
      onToggleAmenity={toggle}
    />
  );
  fireEvent.click(screen.getByText(/EV charger/i));
  expect(toggle).toHaveBeenCalledWith("EV charger");
});
