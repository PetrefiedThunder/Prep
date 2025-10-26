import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BookingCard } from '@/components/listing/booking-card';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/en'
}));

vi.mock('@/components/ui/calendar', () => ({
  Calendar: () => <div role="grid">calendar</div>
}));

describe('BookingCard', () => {
  it('shows price breakdown', () => {
    render(<BookingCard listingId="test" pricePerNight={200} />);
    expect(screen.getByText(/200/)).toBeInTheDocument();
  });

  it('continues to checkout', async () => {
    render(<BookingCard listingId="test" pricePerNight={200} />);
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled();
  });
});
