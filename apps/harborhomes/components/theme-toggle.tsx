'use client';

import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

const getSystemPreference = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches;

export const ThemeToggle = () => {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const prefersDark = getSystemPreference();
    setIsDark(prefersDark);
    document.documentElement.dataset.theme = prefersDark ? 'dark' : 'light';
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
  }, [isDark]);

  return (
    <button
      className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-white"
      onClick={() => setIsDark((prev) => !prev)}
      aria-label="Toggle color mode"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
};
