export interface CityOption {
  slug: string;
  name: string;
  diffKey: string;
  requirementJurisdiction: string;
}

export const CITY_OPTIONS: CityOption[] = [
  {
    slug: 'san-francisco',
    name: 'San Francisco',
    diffKey: 'san_francisco',
    requirementJurisdiction: 'San Francisco'
  },
  {
    slug: 'oakland',
    name: 'Oakland',
    diffKey: 'oakland',
    requirementJurisdiction: 'Oakland'
  },
  {
    slug: 'berkeley',
    name: 'Berkeley',
    diffKey: 'berkeley',
    requirementJurisdiction: 'Berkeley'
  },
  {
    slug: 'san-jose',
    name: 'San Jose',
    diffKey: 'san_jose',
    requirementJurisdiction: 'San Jose'
  },
  {
    slug: 'palo-alto',
    name: 'Palo Alto',
    diffKey: 'palo_alto',
    requirementJurisdiction: 'Palo Alto'
  },
  {
    slug: 'joshua-tree',
    name: 'Joshua Tree',
    diffKey: 'joshua_tree',
    requirementJurisdiction: 'Joshua Tree'
  }
];

export const DEFAULT_CITY = CITY_OPTIONS[0];

export function isCitySlug(value: string | undefined): value is CityOption['slug'] {
  return value !== undefined && CITY_OPTIONS.some((city) => city.slug === value);
}

export function findCityBySlug(slug: string | undefined): CityOption {
  if (slug) {
    const match = CITY_OPTIONS.find((city) => city.slug === slug);
    if (match) {
      return match;
    }
  }
  return DEFAULT_CITY;
}

export function findCityByDiffKey(diffKey: string): CityOption | undefined {
  return CITY_OPTIONS.find((city) => city.diffKey === diffKey);
}
