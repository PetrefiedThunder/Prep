import { render, screen } from '@testing-library/react';
import KitchenBrowser from '../pages/KitchenBrowser';

global.fetch = () => Promise.resolve({ json: () => Promise.resolve([]) }) as any;

describe('KitchenBrowser', () => {
  it('renders heading', async () => {
    render(<KitchenBrowser />);
    expect(screen.getByText(/browse kitchens/i)).toBeInTheDocument();
  });
});
