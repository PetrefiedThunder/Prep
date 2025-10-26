import '@testing-library/jest-dom/vitest';
import React from 'react';

vi.mock('next/image', () => ({
  default: (props: any) => React.createElement('img', props)
}));
