import type { ComponentProps } from 'react';
import HostCalendar, { type HostBooking } from './HostCalendar';

type MetaShape = {
  title: string;
  component: typeof HostCalendar;
  parameters?: Record<string, unknown>;
  args?: Partial<ComponentProps<typeof HostCalendar>>;
};

type StoryShape = {
  args?: Partial<ComponentProps<typeof HostCalendar>>;
  parameters?: Record<string, unknown>;
};

const baseDate = new Date('2024-05-01T15:00:00Z');

const mockBookings: HostBooking[] = [
  {
    id: 'booking-1',
    title: 'Breakfast Prep',
    kitchenName: 'Downtown Kitchen',
    guestName: 'Chef Ada Lovelace',
    start: new Date(baseDate).toISOString(),
    end: new Date(baseDate.getTime() + 90 * 60 * 1000).toISOString(),
    status: 'confirmed',
    seriesId: 'series-42',
    bufferBeforeMinutes: 30,
    bufferAfterMinutes: 15,
    notes: 'Remember to stage dry goods the night before.',
  },
  {
    id: 'booking-2',
    title: 'Dinner Service',
    kitchenName: 'Uptown Test Kitchen',
    guestName: 'Chef Katherine Johnson',
    start: new Date(baseDate.getTime() + 6 * 60 * 60 * 1000).toISOString(),
    end: new Date(baseDate.getTime() + 9 * 60 * 60 * 1000).toISOString(),
    status: 'pending',
    bufferBeforeMinutes: 45,
    bufferAfterMinutes: 30,
    notes: 'Awaiting final headcount confirmation.',
  },
];

const meta = {
  title: 'Components/HostCalendar',
  component: HostCalendar,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Visualizes host bookings and preparation buffers, enabling cancellation of single occurrences or recurring series.',
      },
    },
  },
  args: {
    hostId: 'host-story',
    bookings: mockBookings,
    timezone: 'UTC',
  },
} satisfies MetaShape;

export default meta;

export const Default: StoryShape = {};

export const BusyDay: StoryShape = {
  args: {
    bookings: mockBookings.map((booking, index) =>
      index === 0
        ? {
            ...booking,
            status: 'confirmed',
            notes: 'Series anchor booking with prep windows on both sides.',
          }
        : {
            ...booking,
            status: 'pending',
            bufferBeforeMinutes: 60,
            bufferAfterMinutes: 45,
          },
    ),
  },
};

export const SeriesUnderReview: StoryShape = {
  args: {
    bookings: mockBookings.map((booking) =>
      booking.seriesId
        ? {
            ...booking,
            status: 'pending',
            notes: 'Series cancellation has been requested for this event.',
          }
        : booking,
    ),
  },
};
