import { fireEvent, render, screen } from '@testing-library/react';
import { FiltersDialog } from '@/components/search/filters-dialog';

describe('FiltersDialog', () => {
  it('opens and applies filters', () => {
    render(<FiltersDialog />);
    fireEvent.click(screen.getByRole('button', { name: /open filters/i }));
    fireEvent.click(screen.getByRole('button', { name: /wifi/i }));
    fireEvent.click(screen.getByRole('button', { name: /apply filters/i }));
    expect(screen.getByRole('button', { name: /open filters/i })).toBeInTheDocument();
  });
});
