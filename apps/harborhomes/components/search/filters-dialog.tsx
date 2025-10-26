'use client';

import { useState } from 'react';
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, Input, Label } from '@/components/ui';
import { trackEvent } from '@/lib/analytics';

export interface FiltersDialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export const FiltersDialog = ({ open, onOpenChange }: FiltersDialogProps) => {
  const [price, setPrice] = useState([100, 600]);
  const [amenities, setAmenities] = useState<string[]>([]);

  const toggleAmenity = (amenity: string) => {
    setAmenities((prev) => (prev.includes(amenity) ? prev.filter((a) => a !== amenity) : [...prev, amenity]));
  };

  const applyFilters = () => {
    trackEvent({ name: 'filter_apply', properties: { priceMin: price[0], priceMax: price[1], amenities: amenities.length } });
    onOpenChange?.(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="secondary">Open filters</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Filters</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-6">
          <div>
            <Label className="mb-2 block">Price range</Label>
            <div className="flex items-center gap-3">
              <Input
                type="number"
                min={0}
                value={price[0]}
                onChange={(event) => setPrice([Number(event.target.value), price[1]])}
              />
              <span className="text-muted-ink">to</span>
              <Input
                type="number"
                min={price[0]}
                value={price[1]}
                onChange={(event) => setPrice([price[0], Number(event.target.value)])}
              />
            </div>
          </div>
          <div>
            <Label className="mb-2 block">Amenities</Label>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {['wifi', 'workspace', 'pet-friendly', 'pool', 'ev-charger', 'parking'].map((amenity) => (
                <button
                  key={amenity}
                  onClick={() => toggleAmenity(amenity)}
                  className={`rounded-full border px-3 py-2 text-left capitalize transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                    amenities.includes(amenity) ? 'border-brand bg-brand/10 text-brand' : 'border-border'
                  }`}
                >
                  {amenity.replace('-', ' ')}
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={applyFilters}>Apply filters</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
