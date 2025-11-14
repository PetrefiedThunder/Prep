'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { CalendarIcon, MapPin, Users } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, Tabs, TabsContent, TabsList, TabsTrigger, Button, Input } from '@/components/ui';
import { FiltersDialog } from './filters-dialog';
import { Calendar } from '@/components/ui/calendar';
import { formatRange } from '@/lib/dates';
import { trackEvent } from '@/lib/analytics';

interface SearchState {
  destination: string;
  startDate?: Date;
  endDate?: Date;
  guests: number;
}

export const SearchPill = ({ compact = false }: { compact?: boolean }) => {
  const router = useRouter();
  const params = useSearchParams();
  const pathname = usePathname();
  const localeSegment = pathname.split('/')[1] || 'en';
  const t = useTranslations('search');
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<SearchState>({
    destination: params.get('q') ?? '',
    startDate: params.get('checkin') ? new Date(params.get('checkin') as string) : undefined,
    endDate: params.get('checkout') ? new Date(params.get('checkout') as string) : undefined,
    guests: Number(params.get('guests') ?? 1)
  });
  const [filtersOpen, setFiltersOpen] = useState(false);

  const applySearch = () => {
    const search = new URLSearchParams();
    const destination = state.destination.trim();
    if (destination) search.set('q', destination);
    if (state.startDate) search.set('checkin', state.startDate.toISOString());
    if (state.endDate) search.set('checkout', state.endDate.toISOString());
    if (state.guests) search.set('guests', String(state.guests));
    const query = search.toString();
    router.push(`/${localeSegment}/search${query ? `?${query}` : ''}`);
    trackEvent({ name: 'search', properties: { destination: state.destination, guests: state.guests } });
    setOpen(false);
  };

  return (
    <div className={compact ? 'w-full' : ''}>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <button className="focus-ring inline-flex w-full items-center gap-4 rounded-full border border-border bg-white px-4 py-2 text-left text-sm font-medium shadow-sm transition hover:shadow">
            <span className="flex items-center gap-2 text-muted-ink">
              <MapPin className="h-4 w-4" /> {state.destination || t('where')}
            </span>
            {!compact && (
              <span className="flex items-center gap-2 text-muted-ink">
                <CalendarIcon className="h-4 w-4" />
                {state.startDate && state.endDate
                  ? formatRange(state.startDate.toISOString(), state.endDate.toISOString())
                  : t('when')}
              </span>
            )}
            {!compact && (
              <span className="flex items-center gap-2 text-muted-ink">
                <Users className="h-4 w-4" />
                {state.guests > 0 ? `${state.guests} ${t('guestsLabel')}` : t('guests')}
              </span>
            )}
          </button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Refine your stay</DialogTitle>
          </DialogHeader>
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-muted-ink" htmlFor="destination">
              {t('where')}
            </label>
            <Input
              id="destination"
              value={state.destination}
              onChange={(event) => setState((prev) => ({ ...prev, destination: event.target.value }))}
              placeholder="Explore a city or region"
            />
          </div>
          <Tabs defaultValue="dates">
            <TabsList>
              <TabsTrigger value="dates">Dates</TabsTrigger>
              <TabsTrigger value="guests">Guests</TabsTrigger>
              <TabsTrigger value="filters">Filters</TabsTrigger>
            </TabsList>
            <TabsContent value="dates">
              <Calendar
                mode="range"
                numberOfMonths={compact ? 1 : 2}
                selected={state.startDate && state.endDate ? { from: state.startDate, to: state.endDate } : undefined}
                onSelect={(range) =>
                  setState((prev) => ({
                    ...prev,
                    startDate: range?.from,
                    endDate: range?.to
                  }))
                }
                disabled={{ before: new Date() }}
              />
              <div className="mt-4 flex justify-end">
                <Button onClick={applySearch}>Apply</Button>
              </div>
            </TabsContent>
            <TabsContent value="guests">
              <div className="flex flex-col gap-4">
                <label className="flex items-center justify-between text-sm font-medium">
                  Adults
                  <Input
                    type="number"
                    min={1}
                    value={state.guests}
                    onChange={(event) =>
                      setState((prev) => ({ ...prev, guests: Math.max(1, Number(event.target.value)) }))
                    }
                    className="ml-4 w-24"
                  />
                </label>
                <Button onClick={applySearch}>Apply</Button>
              </div>
            </TabsContent>
            <TabsContent value="filters">
              <FiltersDialog open={filtersOpen} onOpenChange={setFiltersOpen} />
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </div>
  );
};
