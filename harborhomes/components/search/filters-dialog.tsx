"use client";

import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface FiltersDialogProps {
  priceRange: [number, number];
  onPriceChange: (range: [number, number]) => void;
  amenities: string[];
  selectedAmenities: string[];
  onToggleAmenity: (amenity: string) => void;
}

export function FiltersDialog({ priceRange, onPriceChange, amenities, selectedAmenities, onToggleAmenity }: FiltersDialogProps) {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold">Price range</p>
        <div className="mt-4">
          <Slider value={priceRange} min={50} max={1200} step={10} onValueChange={(value) => onPriceChange([value[0], value[1]])} />
          <div className="mt-2 flex justify-between text-sm text-muted-ink">
            <span>${priceRange[0]}</span>
            <span>${priceRange[1]}</span>
          </div>
        </div>
      </div>
      <div>
        <p className="text-sm font-semibold">Amenities</p>
        <ScrollArea className="h-40">
          <div className="grid gap-2 py-2">
            {amenities.map((amenity) => {
              const active = selectedAmenities.includes(amenity);
              return (
                <button
                  key={amenity}
                  onClick={() => onToggleAmenity(amenity)}
                  className={cn(
                    "flex items-center justify-between rounded-2xl border border-border px-4 py-3 text-left text-sm transition",
                    active ? "border-brand bg-brand/10" : "hover:border-brand"
                  )}
                  type="button"
                >
                  {amenity}
                  {active && <span className="text-xs font-semibold text-brand">Added</span>}
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
