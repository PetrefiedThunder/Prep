import { render, screen } from '@testing-library/react';
import { ListingCard } from '@/components/listing/listing-card';
import { listings } from '@/lib/mock-data';

vi.mock('next/navigation', () => ({
  usePathname: () => '/en'
}));

describe('ListingCard', () => {
  it('renders listing information', () => {
    render(<ListingCard listing={listings[0]} />);
    expect(screen.getByText(listings[0].title)).toBeInTheDocument();
    expect(screen.getByText(/night/)).toBeInTheDocument();
  });
});
