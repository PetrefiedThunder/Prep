import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BookingCheckout from '../pages/BookingCheckout';

describe('BookingCheckout', () => {
  it('submits booking', async () => {
    global.fetch = () => Promise.resolve({ ok: true }) as any;
    render(<BookingCheckout />);
    fireEvent.click(screen.getByText(/confirm booking/i));
    await waitFor(() => screen.getByText(/booked!/i));
    expect(screen.getByText(/booked!/i)).toBeInTheDocument();
  });
});
