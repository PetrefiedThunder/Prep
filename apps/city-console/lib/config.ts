const TRAILING_SLASH = /\/+$/;

function sanitizeBaseUrl(value: string): string {
  return value.replace(TRAILING_SLASH, '');
}

export function resolveApiBase(): string {
  const base =
    process.env.PREP_API_BASE ||
    process.env.CITY_CONSOLE_API_BASE ||
    process.env.NEXT_PUBLIC_API_BASE;

  if (!base) {
    throw new Error('City Console API base URL is not configured. Set NEXT_PUBLIC_API_BASE or PREP_API_BASE.');
  }

  return sanitizeBaseUrl(base);
}

export function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  const apiKey = process.env.COMPLIANCE_API_KEY || process.env.CITY_CONSOLE_API_KEY;
  if (apiKey) {
    headers['x-api-key'] = apiKey;
  }

  const bearer = process.env.CITY_CONSOLE_BEARER_TOKEN || process.env.PREP_API_KEY;
  if (bearer) {
    headers.Authorization = bearer.startsWith('Bearer ')
      ? bearer
      : `Bearer ${bearer}`;
  }

  return headers;
}
