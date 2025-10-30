import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

let cachedKey: string | null = null;

function normalizeKey(key: string): string {
  return key.includes('-----BEGIN') ? key : key.replace(/\\n/g, '\n');
}

export function getAuthPublicKey(): string {
  if (cachedKey) {
    return cachedKey;
  }

  const rawKey = process.env.AUTH_SERVICE_PUBLIC_KEY;
  if (rawKey && rawKey.trim().length > 0) {
    cachedKey = normalizeKey(rawKey.trim());
    return cachedKey;
  }

  const keyPath = process.env.AUTH_SERVICE_PUBLIC_KEY_PATH;
  if (keyPath && keyPath.trim().length > 0) {
    const resolved = resolve(keyPath);
    cachedKey = readFileSync(resolved, 'utf-8');
    return cachedKey;
  }

  throw new Error('Auth service public key is not configured');
}
