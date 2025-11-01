'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback } from 'react';

import { CITY_OPTIONS, CityOption } from '@/lib/cities';

interface CitySelectorProps {
  selected: CityOption;
  label?: string;
}

export function CitySelector({ selected, label = 'Jurisdiction' }: CitySelectorProps) {
  const router = useRouter();
  const params = useSearchParams();

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const value = event.target.value;
      const next = new URLSearchParams(params);
      next.set('city', value);
      router.push(`${window.location.pathname}?${next.toString()}`, { scroll: false });
    },
    [params, router]
  );

  return (
    <div className="selector-row">
      <label htmlFor="city-selector">{label}</label>
      <select id="city-selector" value={selected.slug} onChange={handleChange}>
        {CITY_OPTIONS.map((city) => (
          <option key={city.slug} value={city.slug}>
            {city.name}
          </option>
        ))}
      </select>
    </div>
  );
}
