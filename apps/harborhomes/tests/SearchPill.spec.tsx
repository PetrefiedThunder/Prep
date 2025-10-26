import { render, screen } from '@testing-library/react';
import { SearchPill } from '@/components/search/search-pill';
import { NextIntlClientProvider } from 'next-intl';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/en'
}));

describe('SearchPill', () => {
  it('renders default labels', () => {
    render(
      <NextIntlClientProvider
        locale="en"
        messages={{
          search: { where: 'Where', when: 'Any week', guests: 'Add guests', guestsLabel: 'Guests' }
        }}
      >
        <SearchPill />
      </NextIntlClientProvider>
    );
    expect(screen.getByText('Where')).toBeInTheDocument();
  });
});
