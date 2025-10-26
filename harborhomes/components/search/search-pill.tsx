"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Calendar } from "@/components/ui/calendar";
import { addDays } from "date-fns";
import { ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { LabelledCounter } from "@/components/search/selector-counter";
import { FiltersDialog } from "@/components/search/filters-dialog";
import { useTranslations } from "next-intl";
import { track } from "@/lib/analytics";

const AMENITIES = ["EV charger", "Pet friendly", "Workspace", "Self check-in", "Harbor balcony", "Hot tub"];

interface SearchPillProps {
  variant?: "inline" | "stacked";
  onAction?: () => void;
}

export function SearchPill({ variant = "inline", onAction }: SearchPillProps) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("search");

  const [open, setOpen] = useState(false);
  const [guests, setGuests] = useState({ adults: 2, children: 0, infants: 0, pets: 0 });
  const [location, setLocation] = useState(params.get("q") ?? "");
  const [dateRange, setDateRange] = useState<{ from: Date; to: Date } | undefined>(() => {
    const start = params.get("checkin");
    const end = params.get("checkout");
    return start && end ? { from: new Date(start), to: new Date(end) } : undefined;
  });
  const [priceRange, setPriceRange] = useState<[number, number]>([
    Number(params.get("minPrice") ?? 100),
    Number(params.get("maxPrice") ?? 800)
  ]);
  const [selectedAmenities, setSelectedAmenities] = useState<string[]>(params.getAll("amenities"));

  useEffect(() => {
    if (!open) {
      setLocation(params.get("q") ?? "");
    }
  }, [open, params]);

  const summary = useMemo(() => {
    const locationText = location || "Anywhere";
    const dateText = dateRange ? `${dateRange.from.toLocaleDateString()} – ${dateRange.to?.toLocaleDateString()}` : "Any week";
    const guestCount = guests.adults + guests.children;
    const guestText = guestCount ? `${guestCount} guests` : "Add guests";
    return `${locationText} · ${dateText} · ${guestText}`;
  }, [dateRange, guests, location]);

  const applySearch = () => {
    const search = new URLSearchParams();
    if (location) search.set("q", location);
    if (dateRange?.from) search.set("checkin", dateRange.from.toISOString().split("T")[0]);
    if (dateRange?.to) search.set("checkout", dateRange.to.toISOString().split("T")[0]);
    const totalGuests = guests.adults + guests.children + guests.infants;
    if (totalGuests) search.set("guests", totalGuests.toString());
    search.set("minPrice", String(priceRange[0]));
    search.set("maxPrice", String(priceRange[1]));
    selectedAmenities.forEach((amenity) => search.append("amenities", amenity));
    router.push(`${pathname === "/" ? "/search" : pathname}?${search.toString()}`);
    track({ type: "search", query: location || "", guests: guests.adults + guests.children, startDate: dateRange?.from?.toISOString(), endDate: dateRange?.to?.toISOString() });
    setOpen(false);
    onAction?.();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          className={cn(
            "flex w-full items-center justify-between gap-3 rounded-full border border-border bg-white px-4 py-2 text-left text-sm shadow-sm transition hover:shadow-md",
            variant === "stacked" && "flex-col items-start gap-1 rounded-3xl px-5 py-4"
          )}
          aria-label="Open search"
        >
          <div className="flex flex-col">
            <span className="font-medium">{t("title")}</span>
            <span className="text-xs text-muted-ink">{summary}</span>
          </div>
          <span className="rounded-full bg-brand p-2 text-brand-contrast">
            <Search className="h-4 w-4" />
          </span>
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Plan your next stay</DialogTitle>
        </DialogHeader>
        <Tabs defaultValue="where">
          <TabsList className="w-full justify-start">
            <TabsTrigger value="where">Where</TabsTrigger>
            <TabsTrigger value="dates">Dates</TabsTrigger>
            <TabsTrigger value="guests">Guests</TabsTrigger>
            <TabsTrigger value="filters">{t("filters")}</TabsTrigger>
          </TabsList>
          <TabsContent value="where" className="mt-6">
            <Input
              placeholder="Search by city, neighborhood, or experience"
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              autoFocus
            />
          </TabsContent>
          <TabsContent value="dates" className="mt-6">
            <Calendar
              mode="range"
              selected={dateRange}
              onSelect={(range) =>
                setDateRange(
                  range?.from && range.to
                    ? { from: range.from, to: range.to }
                    : range?.from
                      ? { from: range.from, to: addDays(range.from, 4) }
                      : undefined
                )
              }
              numberOfMonths={2}
              disabled={(date) => date < new Date()}
            />
          </TabsContent>
          <TabsContent value="guests" className="mt-6 grid gap-4">
            <LabelledCounter
              label="Adults"
              helper="Ages 13+"
              value={guests.adults}
              onChange={(value) => setGuests((prev) => ({ ...prev, adults: Math.max(1, value) }))}
            />
            <LabelledCounter
              label="Children"
              helper="Ages 2-12"
              value={guests.children}
              onChange={(value) => setGuests((prev) => ({ ...prev, children: Math.max(0, value) }))}
            />
            <LabelledCounter
              label="Infants"
              helper="Under 2"
              value={guests.infants}
              onChange={(value) => setGuests((prev) => ({ ...prev, infants: Math.max(0, value) }))}
            />
            <LabelledCounter
              label="Pets"
              helper="Service animals welcome"
              value={guests.pets}
              onChange={(value) => setGuests((prev) => ({ ...prev, pets: Math.max(0, value) }))}
            />
          </TabsContent>
          <TabsContent value="filters" className="mt-6">
            <FiltersDialog
              priceRange={priceRange}
              onPriceChange={(range) => setPriceRange(range)}
              amenities={AMENITIES}
              selectedAmenities={selectedAmenities}
              onToggleAmenity={(amenity) =>
                setSelectedAmenities((prev) =>
                  prev.includes(amenity) ? prev.filter((item) => item !== amenity) : [...prev, amenity]
                )
              }
            />
          </TabsContent>
        </Tabs>
        <div className="flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={applySearch}>Search</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
