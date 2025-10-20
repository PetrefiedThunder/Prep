import { render, screen, waitFor } from '@testing-library/react';
import Dashboard from '../pages/Dashboard';

global.fetch = () => Promise.resolve({ json: () => Promise.resolve({ bookings: 5 }) }) as any;

describe('Dashboard', () => {
  it('shows bookings stat', async () => {
    render(<Dashboard />);
    await waitFor(() => screen.getByText(/bookings:/i));
    expect(screen.getByText(/bookings: 5/i)).toBeInTheDocument();
  });
});
