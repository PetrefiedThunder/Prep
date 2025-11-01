import { cache } from 'react';

import type { FeeFrequency, FeeLineItem } from '@/components/compliance/fee-card';
import type { PermitBadgeProps, PermitStatus } from '@/components/compliance/permit-badge';
import type { RequirementItem, RequirementStatus } from '@/components/compliance/requirements-list';

export interface CityComplianceSnapshot {
  slug: string;
  city: string;
  state: string;
  displayName: string;
  summary: string;
  updatedAt?: string;
  fees: FeeLineItem[];
  requirements: RequirementItem[];
  permits: PermitBadgeProps[];
}

const FALLBACK_SNAPSHOTS: Record<string, CityComplianceSnapshot> = {
  'san-francisco-ca': {
    slug: 'san-francisco-ca',
    city: 'San Francisco',
    state: 'CA',
    displayName: 'San Francisco, CA',
    summary:
      'Urban kitchens must keep permits aligned with San Francisco Department of Public Health timelines and the shared-spaces ordinance.',
    updatedAt: '2024-05-15T08:00:00Z',
    fees: [
      {
        id: 'sf-health-renewal',
        name: 'Annual Health Permit',
        amount: 742,
        frequency: 'annual',
        due: '2024-07-31',
        description: 'Covers San Francisco Department of Public Health inspection program and commercial kitchen oversight.'
      },
      {
        id: 'sf-fire-life-safety',
        name: 'Fire Life Safety Sign-off',
        amount: 180,
        frequency: 'annual',
        due: '2024-05-01',
        description: 'Mandatory for shared kitchens maintaining Type-1 hoods with active suppression systems.'
      },
      {
        id: 'sf-shared-space',
        name: 'Shared Spaces Compliance Filing',
        amount: 96,
        frequency: 'quarterly',
        due: '2024-06-15',
        description: 'Quarterly declaration of off-site food preparation volume supporting shared-space partners.'
      }
    ],
    requirements: [
      {
        id: 'sf-manager-cert',
        title: 'Certified Food Protection Manager on duty',
        status: 'met',
        detail: 'Documentation verified by Prep onboarding team (ServSafe certificate #SF-44821).'
      },
      {
        id: 'sf-hazard-plan',
        title: 'Hazard analysis and risk-based preventive controls plan',
        status: 'pending',
        detail: 'Awaiting upload of allergen cross-contact mitigation addendum from operations team.',
        due: '2024-06-10'
      },
      {
        id: 'sf-worker-reg',
        title: 'San Francisco labor compliance attestation',
        status: 'overdue',
        detail: 'City requires updated attestation covering scheduling predictability ordinance.',
        due: '2024-05-20'
      }
    ],
    permits: [
      {
        name: 'San Francisco DPH Health Permit',
        status: 'active',
        issuedBy: 'San Francisco Department of Public Health',
        permitNumber: 'SF-HP-009331',
        expiresOn: '2024-07-31'
      },
      {
        name: 'Fire Department Operational Permit',
        status: 'expiring',
        issuedBy: 'San Francisco Fire Department',
        permitNumber: 'SFFD-OP-77612',
        expiresOn: '2024-05-28'
      }
    ]
  },
  'joshua-tree-ca': {
    slug: 'joshua-tree-ca',
    city: 'Joshua Tree',
    state: 'CA',
    displayName: 'Joshua Tree, CA',
    summary:
      'Desert ghost kitchens coordinate with San Bernardino County for cottage and commercial prep while tracking BLM special use filings.',
    updatedAt: '2024-04-28T08:00:00Z',
    fees: [
      {
        id: 'jt-environmental',
        name: 'Environmental Health Permit',
        amount: 392,
        frequency: 'annual',
        due: '2024-09-30',
        description: 'County environmental health services fee for high-risk food production facilities.'
      },
      {
        id: 'jt-short-term-rental',
        name: 'Short-Term Rental Compliance',
        amount: 129,
        frequency: 'annual',
        due: '2024-08-15',
        description: 'Maintains operational license for commissary linked to short-term rental offerings.'
      },
      {
        id: 'jt-water-testing',
        name: 'Quarterly Water Quality Testing',
        amount: 210,
        frequency: 'quarterly',
        due: '2024-06-05',
        description: 'Required for wells supporting commissary ice machines and dish stations.'
      }
    ],
    requirements: [
      {
        id: 'jt-servsafe',
        title: 'Food handler cards for all seasonal staff',
        status: 'pending',
        detail: 'Two seasonal hires still need California food handler certificates.',
        due: '2024-05-25'
      },
      {
        id: 'jt-water-plan',
        title: 'Water safety plan acknowledgement',
        status: 'met',
        detail: 'Signed acknowledgement filed with San Bernardino Department of Public Health.'
      },
      {
        id: 'jt-blm-filings',
        title: 'BLM special use renewal package',
        status: 'overdue',
        detail: 'Need to submit renewal for mobile prep trailer located on BLM managed land.',
        due: '2024-04-30'
      }
    ],
    permits: [
      {
        name: 'San Bernardino County Health Permit',
        status: 'active',
        issuedBy: 'San Bernardino County Environmental Health',
        permitNumber: 'SB-ENV-44107',
        expiresOn: '2024-09-30'
      },
      {
        name: 'BLM Special Recreation Permit',
        status: 'expired',
        issuedBy: 'U.S. Bureau of Land Management',
        permitNumber: 'BLM-SRP-2023-514',
        expiresOn: '2024-03-31'
      }
    ]
  }
};

const normalizeFrequency = (value: unknown): FeeFrequency | undefined => {
  if (!value) return undefined;
  const normalized = String(value).toLowerCase().replace(/[-\s]/g, '_');
  const allowed: FeeFrequency[] = ['one_time', 'annual', 'semiannual', 'quarterly', 'monthly'];
  return allowed.includes(normalized as FeeFrequency) ? (normalized as FeeFrequency) : undefined;
};

const normalizeRequirementStatus = (value: unknown): RequirementStatus => {
  const normalized = String(value ?? '').toLowerCase();
  if (normalized.includes('overdue') || normalized.includes('late')) return 'overdue';
  if (normalized.includes('pending') || normalized.includes('progress')) return 'pending';
  return 'met';
};

const normalizePermitStatus = (value: unknown): PermitStatus => {
  const normalized = String(value ?? '').toLowerCase();
  if (normalized.includes('expired') || normalized.includes('revoked')) return 'expired';
  if (normalized.includes('expir') || normalized.includes('renew') || normalized.includes('pending')) {
    return 'expiring';
  }
  return 'active';
};

const coerceAmount = (value: unknown, fallback: number) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value.replace(/[^0-9.-]/g, ''));
    if (!Number.isNaN(parsed)) return parsed;
  }
  if (typeof value === 'object' && value && 'amount_cents' in (value as Record<string, unknown>)) {
    const cents = (value as Record<string, unknown>).amount_cents;
    if (typeof cents === 'number') return Math.round(cents / 100);
  }
  return fallback;
};

const mergeSnapshot = (slug: string, overrides: Partial<CityComplianceSnapshot>) => {
  const fallback = FALLBACK_SNAPSHOTS[slug];
  if (!fallback) {
    return {
      slug,
      city: overrides.city ?? slug,
      state: overrides.state ?? '',
      displayName: overrides.displayName ?? slug,
      summary: overrides.summary ?? '',
      updatedAt: overrides.updatedAt,
      fees: overrides.fees ?? [],
      requirements: overrides.requirements ?? [],
      permits: overrides.permits ?? []
    } satisfies CityComplianceSnapshot;
  }

  return {
    ...fallback,
    ...overrides,
    fees: overrides.fees ?? fallback.fees,
    requirements: overrides.requirements ?? fallback.requirements,
    permits: overrides.permits ?? fallback.permits,
  } satisfies CityComplianceSnapshot;
};

const normalizeFromApi = (slug: string, payload: any): CityComplianceSnapshot => {
  const overrides: Partial<CityComplianceSnapshot> = {};
  if (payload?.city) {
    const cityName = payload.city.name ?? payload.city.city ?? payload.city.title ?? FALLBACK_SNAPSHOTS[slug]?.city ?? slug;
    const state = payload.city.state ?? payload.city.region ?? FALLBACK_SNAPSHOTS[slug]?.state ?? '';
    overrides.city = cityName;
    overrides.state = state;
    overrides.displayName = `${cityName}${state ? `, ${state}` : ''}`;
  }
  if (payload?.summary) {
    overrides.summary = payload.summary;
  } else if (payload?.description) {
    overrides.summary = payload.description;
  }
  overrides.updatedAt = payload?.updated_at ?? payload?.updatedAt ?? FALLBACK_SNAPSHOTS[slug]?.updatedAt;

  if (Array.isArray(payload?.fees)) {
    overrides.fees = payload.fees.map((fee: any, index: number): FeeLineItem => ({
      id: String(fee.id ?? `${slug}-fee-${index}`),
      name: fee.name ?? fee.title ?? `Fee ${index + 1}`,
      amount: coerceAmount(fee.amount ?? fee.total ?? fee.amount_cents, FALLBACK_SNAPSHOTS[slug]?.fees[index]?.amount ?? 0),
      frequency: normalizeFrequency(fee.frequency ?? fee.cadence ?? fee.schedule),
      due: fee.due ?? fee.due_on ?? fee.dueDate,
      description: fee.description ?? fee.details ?? undefined,
    }));
  }

  if (Array.isArray(payload?.requirements)) {
    overrides.requirements = payload.requirements.map((item: any, index: number): RequirementItem => ({
      id: String(item.id ?? `${slug}-req-${index}`),
      title: item.title ?? item.name ?? `Requirement ${index + 1}`,
      status: normalizeRequirementStatus(item.status),
      detail: item.detail ?? item.description ?? undefined,
      due: item.due ?? item.due_on ?? item.deadline,
    }));
  }

  if (Array.isArray(payload?.permits)) {
    overrides.permits = payload.permits.map((permit: any, index: number): PermitBadgeProps => ({
      name: permit.name ?? permit.title ?? `Permit ${index + 1}`,
      status: normalizePermitStatus(permit.status) as PermitStatus,
      permitNumber: permit.permit_number ?? permit.number ?? permit.id,
      issuedBy: permit.issued_by ?? permit.agency ?? undefined,
      expiresOn: permit.expires_on ?? permit.expiry ?? permit.expiresAt,
    }));
  }

  return mergeSnapshot(slug, overrides);
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;

const fetchCitySnapshot = async (slug: string): Promise<CityComplianceSnapshot> => {
  if (!API_BASE) {
    return mergeSnapshot(slug, {});
  }

  const base = API_BASE.replace(/\/+$/, '');
  const url = `${base}/api/v1/cities/${slug}/compliance-summary`;

  try {
    const response = await fetch(url, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    if (!response.ok) {
      console.warn(`Policy API responded with ${response.status} for ${slug}`);
      return mergeSnapshot(slug, {});
    }

    const payload = await response.json();
    return normalizeFromApi(slug, payload);
  } catch (error) {
    console.error('Unable to load policy snapshot', error);
    return mergeSnapshot(slug, {});
  }
};

export const loadCityCompliance = cache(fetchCitySnapshot);

export const getPolicyDemoCities = () => [
  FALLBACK_SNAPSHOTS['san-francisco-ca'],
  FALLBACK_SNAPSHOTS['joshua-tree-ca'],
];
