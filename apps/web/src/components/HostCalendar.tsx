import { useEffect, useMemo, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { EventClickArg, EventContentArg, EventInput } from '@fullcalendar/core';
import { addMinutes, subMinutes } from 'date-fns';

export type HostBookingStatus = 'confirmed' | 'pending' | 'cancelled' | 'blocked';

export interface HostBooking {
  id: string;
  title?: string;
  kitchenName?: string;
  guestName?: string;
  start: string;
  end: string;
  status: HostBookingStatus;
  seriesId?: string | null;
  bufferBeforeMinutes?: number | null;
  bufferAfterMinutes?: number | null;
  notes?: string | null;
}

export interface HostCalendarProps {
  hostId: string;
  /** ISO date used for the initial week shown by the calendar. */
  initialDate?: string;
  /** Time zone identifier used for time labels and formatting. */
  timezone?: string;
  /**
   * Optional set of bookings that will be rendered instead of fetching from the
   * backend. Useful for Storybook and tests.
   */
  bookings?: HostBooking[];
  /** Callback invoked whenever bookings are updated in the component. */
  onBookingsChange?: (bookings: HostBooking[]) => void;
}

type CancelActionState = 'idle' | 'single' | 'series';

type LoadedBookings = HostBooking[];

const BOOKING_ENDPOINT = (hostId: string) => `/api/hosts/${hostId}/calendar`;
const CANCEL_BOOKING_ENDPOINT = (hostId: string, bookingId: string) =>
  `/api/hosts/${hostId}/calendar/bookings/${bookingId}`;
const CANCEL_SERIES_ENDPOINT = (hostId: string, seriesId: string) =>
  `/api/hosts/${hostId}/calendar/series/${seriesId}`;

const BUFFER_CLASSNAMES = {
  before: ['host-calendar-buffer', 'buffer-before'],
  after: ['host-calendar-buffer', 'buffer-after'],
} as const;

const STATUS_CLASS_MAP: Record<HostBookingStatus, string[]> = {
  confirmed: ['host-calendar-event', 'status-confirmed'],
  pending: ['host-calendar-event', 'status-pending'],
  cancelled: ['host-calendar-event', 'status-cancelled'],
  blocked: ['host-calendar-event', 'status-blocked'],
};

const formatRange = (startIso: string, endIso: string, timezone?: string) => {
  try {
    const formatter = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      timeZone: timezone,
    });

    return `${formatter.format(new Date(startIso))} – ${formatter.format(new Date(endIso))}`;
  } catch (error) {
    // Fallback when the time zone is invalid.
    return `${new Date(startIso).toLocaleTimeString()} – ${new Date(endIso).toLocaleTimeString()}`;
  }
};

const getBufferEvent = (
  booking: HostBooking,
  type: 'before' | 'after',
  minutes: number,
): EventInput => {
  const startDate = new Date(booking.start);
  const endDate = new Date(booking.end);
  const start = type === 'before' ? subMinutes(startDate, minutes) : endDate;
  const end = type === 'before' ? startDate : addMinutes(endDate, minutes);

  return {
    id: `${booking.id}-buffer-${type}`,
    start: start.toISOString(),
    end: end.toISOString(),
    display: 'background',
    classNames: [...BUFFER_CLASSNAMES[type]],
    extendedProps: {
      type: 'buffer',
      bufferType: type,
      booking,
    },
  } satisfies EventInput;
};

const toCalendarEvents = (bookings: LoadedBookings): EventInput[] =>
  bookings.flatMap((booking) => {
    const events: EventInput[] = [
      {
        id: booking.id,
        title: booking.title ?? booking.kitchenName ?? 'Booking',
        start: booking.start,
        end: booking.end,
        classNames: STATUS_CLASS_MAP[booking.status] ?? STATUS_CLASS_MAP.confirmed,
        extendedProps: {
          type: 'booking',
          booking,
        },
      },
    ];

    if (booking.bufferBeforeMinutes) {
      events.push(getBufferEvent(booking, 'before', booking.bufferBeforeMinutes));
    }

    if (booking.bufferAfterMinutes) {
      events.push(getBufferEvent(booking, 'after', booking.bufferAfterMinutes));
    }

    return events;
  });

const renderEventContent = (
  arg: EventContentArg,
  timezone?: string,
): JSX.Element => {
  const eventType = (arg.event.extendedProps as { type?: string }).type;

  if (eventType === 'buffer') {
    const bufferType = (arg.event.extendedProps as { bufferType?: 'before' | 'after' }).bufferType;
    const label = bufferType === 'before' ? 'Prep Buffer' : 'Cleanup Buffer';

    return (
      <span className="text-xs font-medium text-amber-700" data-testid="buffer-label">
        {label}
      </span>
    );
  }

  const booking = (arg.event.extendedProps as { booking?: HostBooking }).booking;

  if (!booking) {
    return <span>{arg.event.title}</span>;
  }

  return (
    <div className="flex flex-col text-left text-xs md:text-sm" data-testid="booking-event">
      <span className="font-medium text-slate-900">
        {booking.title ?? booking.kitchenName ?? 'Booking'}
      </span>
      <span className="text-slate-600">{formatRange(booking.start, booking.end, timezone)}</span>
      {booking.guestName ? (
        <span className="text-slate-500">Guest: {booking.guestName}</span>
      ) : null}
      {booking.status !== 'confirmed' ? (
        <span className="uppercase tracking-wide text-[10px] text-slate-500">{booking.status}</span>
      ) : null}
    </div>
  );
};

const DEFAULT_NO_BOOKINGS = 'No bookings scheduled for the selected period.';

const HostCalendar = ({
  hostId,
  initialDate,
  timezone = 'UTC',
  bookings: providedBookings,
  onBookingsChange,
}: HostCalendarProps) => {
  const [internalBookings, setInternalBookings] = useState<LoadedBookings>(providedBookings ?? []);
  const [loading, setLoading] = useState<boolean>(!providedBookings);
  const [error, setError] = useState<string | null>(null);
  const [selectedBooking, setSelectedBooking] = useState<HostBooking | null>(null);
  const [actionState, setActionState] = useState<CancelActionState>('idle');
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (providedBookings) {
      setInternalBookings(providedBookings);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(BOOKING_ENDPOINT(hostId));

        if (!response.ok) {
          throw new Error('Failed to load host calendar.');
        }

        const payload = await response.json();
        const bookings: LoadedBookings = Array.isArray(payload)
          ? payload
          : (payload?.bookings as LoadedBookings | undefined) ?? [];

        if (!cancelled) {
          setInternalBookings(bookings);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load host calendar.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [hostId, providedBookings]);

  useEffect(() => {
    if (!providedBookings) {
      return;
    }

    setInternalBookings(providedBookings);
  }, [providedBookings]);

  useEffect(() => {
    if (!selectedBooking) {
      return;
    }

    const updated = internalBookings.find((booking) => booking.id === selectedBooking.id);

    if (updated && updated !== selectedBooking) {
      setSelectedBooking(updated);
    }
  }, [internalBookings, selectedBooking]);

  const events = useMemo<EventInput[]>(() => toCalendarEvents(internalBookings), [internalBookings]);

  const updateBookings = (updater: (bookings: LoadedBookings) => LoadedBookings) => {
    setInternalBookings((prev) => {
      const next = updater(prev);
      onBookingsChange?.(next);
      return next;
    });
  };

  const handleEventClick = (arg: EventClickArg) => {
    const type = (arg.event.extendedProps as { type?: string }).type;

    if (type === 'buffer') {
      return;
    }

    const booking = (arg.event.extendedProps as { booking?: HostBooking }).booking;

    if (!booking) {
      return;
    }

    setSelectedBooking(booking);
    setActionFeedback(null);
    setActionState('idle');
  };

  const closeDialog = () => {
    setSelectedBooking(null);
    setActionFeedback(null);
    setActionState('idle');
  };

  const cancelOccurrence = async () => {
    if (!selectedBooking) {
      return;
    }

    setActionState('single');
    setActionFeedback(null);

    try {
      const response = await fetch(CANCEL_BOOKING_ENDPOINT(hostId, selectedBooking.id), {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Unable to cancel the selected booking.');
      }

      updateBookings((prev) =>
        prev.map((booking) =>
          booking.id === selectedBooking.id ? { ...booking, status: 'cancelled' } : booking,
        ),
      );

      setActionFeedback('Booking cancelled successfully.');
    } catch (err) {
      setActionFeedback(err instanceof Error ? err.message : 'Cancellation failed.');
    } finally {
      setActionState('idle');
    }
  };

  const cancelSeries = async () => {
    if (!selectedBooking?.seriesId) {
      return;
    }

    setActionState('series');
    setActionFeedback(null);

    try {
      const response = await fetch(CANCEL_SERIES_ENDPOINT(hostId, selectedBooking.seriesId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'cancel' }),
      });

      if (!response.ok) {
        throw new Error('Unable to cancel the series.');
      }

      updateBookings((prev) =>
        prev.map((booking) =>
          booking.seriesId === selectedBooking.seriesId ? { ...booking, status: 'cancelled' } : booking,
        ),
      );

      setActionFeedback('Series cancellation requested.');
    } catch (err) {
      setActionFeedback(err instanceof Error ? err.message : 'Series cancellation failed.');
    } finally {
      setActionState('idle');
    }
  };

  const isCancellingSingle = actionState === 'single';
  const isCancellingSeries = actionState === 'series';

  return (
    <div className="flex flex-col gap-4" data-testid="host-calendar">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Host Calendar</h2>
            <p className="text-sm text-slate-600">
              Review bookings, prep buffers, and take action on upcoming events.
            </p>
          </div>
        </div>

        {loading ? (
          <div role="status" className="py-8 text-center text-sm text-slate-500">
            Loading calendar…
          </div>
        ) : error ? (
          <div role="alert" className="rounded-md bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : events.length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-500">{DEFAULT_NO_BOOKINGS}</div>
        ) : (
          <FullCalendar
            plugins={[timeGridPlugin, interactionPlugin]}
            initialView="timeGridWeek"
            height="auto"
            events={events}
            initialDate={initialDate}
            eventClick={handleEventClick}
            eventContent={(arg) => renderEventContent(arg, timezone)}
            nowIndicator
            slotDuration="00:30:00"
            slotLabelFormat={{ hour: 'numeric', minute: '2-digit', hour12: true }}
            displayEventTime={false}
          />
        )}
      </div>

      {selectedBooking ? (
        <div
          role="dialog"
          aria-modal="true"
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                {selectedBooking.title ?? selectedBooking.kitchenName ?? 'Booking details'}
              </h3>
              <p className="text-sm text-slate-600">
                {formatRange(selectedBooking.start, selectedBooking.end, timezone)}
              </p>
              {selectedBooking.guestName ? (
                <p className="text-sm text-slate-500">Guest: {selectedBooking.guestName}</p>
              ) : null}
              {selectedBooking.notes ? (
                <p className="mt-2 text-sm text-slate-500">{selectedBooking.notes}</p>
              ) : null}
              <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">
                Status: {selectedBooking.status}
              </p>
            </div>
            <button
              type="button"
              className="rounded-md border border-transparent px-3 py-1 text-sm text-slate-500 hover:text-slate-700"
              onClick={closeDialog}
            >
              Close
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={cancelOccurrence}
              disabled={isCancellingSingle}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-red-300"
            >
              {isCancellingSingle ? 'Cancelling…' : 'Cancel this occurrence'}
            </button>
            {selectedBooking.seriesId ? (
              <button
                type="button"
                onClick={cancelSeries}
                disabled={isCancellingSeries}
                className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-amber-300"
              >
                {isCancellingSeries ? 'Cancelling series…' : 'Cancel entire series'}
              </button>
            ) : null}
          </div>

          {actionFeedback ? (
            <p className="mt-4 text-sm text-slate-600" role="status">
              {actionFeedback}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

export default HostCalendar;
