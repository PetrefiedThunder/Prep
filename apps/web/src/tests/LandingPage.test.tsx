import { render, screen } from '@testing-library/react';
import LandingPage from '../pages/LandingPage';

describe('LandingPage', () => {
  it('renders welcome text', () => {
    render(<LandingPage />);
    expect(screen.getByText(/welcome to prep/i)).toBeInTheDocument();
  });
});
