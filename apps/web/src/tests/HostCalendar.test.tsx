import { vi } from 'vitest';
import { isValidElement } from 'react';

vi.mock('@fullcalendar/react', () => ({
  __esModule: true,
  default: ({ events, eventContent, eventClick }: any) => (
    <div data-testid="fullcalendar-mock">
      {events.map((event: any) => {
        const contentResult = eventContent
          ? eventContent({
              event: {
                ...event,
                extendedProps: event.extendedProps ?? {},
                start: event.start ? new Date(event.start) : null,
                end: event.end ? new Date(event.end) : null,
              },
            })
          : event.title;

        return (
          <div key={event.id} data-testid={`event-${event.id}`}>
            <div data-testid={`event-content-${event.id}`}>
              {isValidElement(contentResult) ? contentResult : <span>{String(contentResult)}</span>}
            </div>
            <button type="button" onClick={() => eventClick?.({ event })}>
              Manage
            </button>
          </div>
        );
      })}
    </div>
  ),
}));

vi.mock('@fullcalendar/timegrid', () => ({ __esModule: true, default: {} }));
vi.mock('@fullcalendar/interaction', () => ({ __esModule: true, default: {} }));

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HostCalendar, { type HostBooking } from '../components/HostCalendar';

type FetchArgs = Parameters<typeof fetch>;

const createResponse = (data: unknown, ok = true, status = 200) =>
  Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(data),
  }) as unknown as Response;

describe('HostCalendar', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads host bookings and renders prep buffers', async () => {
    const bookings: HostBooking[] = [
      {
        id: 'booking-1',
        kitchenName: 'Kitchen Prep Session',
        start: '2024-05-01T10:00:00.000Z',
        end: '2024-05-01T12:00:00.000Z',
        status: 'confirmed',
        bufferBeforeMinutes: 30,
        bufferAfterMinutes: 15,
        guestName: 'Chef Ada',
      },
    ];

    const fetchMock = vi
      .fn<FetchArgs, Promise<Response>>()
      .mockResolvedValueOnce(createResponse({ bookings }));

    global.fetch = fetchMock as unknown as typeof fetch;

    render(<HostCalendar hostId="host-123" timezone="UTC" />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/hosts/host-123/calendar');
    });

    expect(await screen.findByText(/Kitchen Prep Session/i)).toBeInTheDocument();

    const buffers = await screen.findAllByTestId('buffer-label');
    const bufferTexts = buffers.map((element) => element.textContent);

    expect(bufferTexts).toEqual(expect.arrayContaining(['Prep Buffer', 'Cleanup Buffer']));
  });

  it('cancels a single booking occurrence', async () => {
    const bookings: HostBooking[] = [
      {
        id: 'booking-99',
        title: 'Tasting Menu Run-through',
        start: '2024-05-02T15:00:00.000Z',
        end: '2024-05-02T17:00:00.000Z',
        status: 'confirmed',
        seriesId: 'series-9',
        bufferBeforeMinutes: 20,
      },
    ];

    const fetchMock = vi
      .fn<FetchArgs, Promise<Response>>()
      .mockResolvedValueOnce(createResponse({ bookings }))
      .mockResolvedValueOnce(createResponse({}));

    global.fetch = fetchMock as unknown as typeof fetch;

    render(<HostCalendar hostId="host-321" timezone="UTC" />);

    const manageButtons = await screen.findAllByRole('button', { name: /Manage/i });
    const user = userEvent.setup();

    await user.click(manageButtons[0]);

    const cancelOccurrence = await screen.findByRole('button', {
      name: /Cancel this occurrence/i,
    });

    await user.click(cancelOccurrence);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith(
        '/api/hosts/host-321/calendar/bookings/booking-99',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Booking cancelled successfully/i)).toBeInTheDocument();
    });
  });

  it('cancels every booking in a series', async () => {
    const bookings: HostBooking[] = [
      {
        id: 'booking-1',
        title: 'Weekly Prep',
        start: '2024-05-03T08:00:00.000Z',
        end: '2024-05-03T10:00:00.000Z',
        status: 'confirmed',
        seriesId: 'series-100',
        bufferBeforeMinutes: 15,
      },
      {
        id: 'booking-2',
        title: 'Weekly Prep',
        start: '2024-05-10T08:00:00.000Z',
        end: '2024-05-10T10:00:00.000Z',
        status: 'confirmed',
        seriesId: 'series-100',
      },
    ];

    const fetchMock = vi
      .fn<FetchArgs, Promise<Response>>()
      .mockResolvedValueOnce(createResponse({ bookings }))
      .mockResolvedValueOnce(createResponse({}));

    global.fetch = fetchMock as unknown as typeof fetch;

    render(<HostCalendar hostId="host-555" timezone="UTC" />);

    const manageButtons = await screen.findAllByRole('button', { name: /Manage/i });
    const user = userEvent.setup();

    await user.click(manageButtons[0]);

    const cancelSeries = await screen.findByRole('button', {
      name: /Cancel entire series/i,
    });

    await user.click(cancelSeries);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith(
        '/api/hosts/host-555/calendar/series/series-100',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });

    const lastCall = (fetchMock.mock.calls.at(-1) ?? []) as FetchArgs;
    const options = (lastCall[1] ?? {}) as RequestInit;

    expect(options.body ? JSON.parse(options.body.toString()) : null).toEqual({ action: 'cancel' });

    await waitFor(() => {
      expect(screen.getByText(/Series cancellation requested/i)).toBeInTheDocument();
    });
  });
});
