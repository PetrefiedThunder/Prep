export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface LogOptions {
  metadata?: Record<string, unknown>
  context?: Record<string, unknown>
  error?: unknown
  whitelist?: string[]
}

const REDACTED_KEYS = new Set([
  'apikey',
  'api_key',
  'token',
  'access_token',
  'refresh_token',
  'authorization',
  'password',
  'secret',
  'client_secret',
  'stripe_secret_key',
  'credential',
])

const DEFAULT_WHITELIST = new Set<string>([
  'eventType',
  'paymentIntentId',
  'bookingId',
  'status',
  'requestId',
])

const SECRET_PATTERNS = [
  /(sk|rk)_(test|live)_[0-9a-zA-Z]+/i,
  /pk_(test|live)_[0-9a-zA-Z]+/i,
  /client_secret_[0-9a-zA-Z]+/i,
  /bearer\s+[0-9a-zA-Z._-]+/i,
  /eyJ[a-zA-Z0-9_-]{10,}/, // JWT-like tokens
]

function redactString(value: string): string {
  if (SECRET_PATTERNS.some((pattern) => pattern.test(value))) {
    return '[REDACTED]'
  }

  return value
}

function shouldRedactKey(key: string, whitelist: Set<string>): boolean {
  const normalizedKey = key.toLowerCase()
  return REDACTED_KEYS.has(normalizedKey) && !whitelist.has(key)
}

function sanitizeValue(
  value: unknown,
  whitelist: Set<string>,
  parentKey?: string
): unknown {
  if (value === null || value === undefined) return value
  if (typeof value === 'string') return redactString(value)
  if (typeof value === 'number' || typeof value === 'boolean') return value
  if (Array.isArray(value)) return value.map((entry) => sanitizeValue(entry, whitelist))

  if (value instanceof Error) {
    return {
      name: value.name,
      message: redactString(value.message),
    }
  }

  if (typeof value === 'object') {
    const sanitizedEntries: Record<string, unknown> = {}
    for (const [key, entryValue] of Object.entries(value as Record<string, unknown>)) {
      if (shouldRedactKey(key, whitelist)) {
        sanitizedEntries[key] = '[REDACTED]'
        continue
      }

      sanitizedEntries[key] = sanitizeValue(entryValue, whitelist, key)
    }

    return sanitizedEntries
  }

  return parentKey && shouldRedactKey(parentKey, whitelist) ? '[REDACTED]' : value
}

function buildWhitelist(extra: string[] | undefined): Set<string> {
  const whitelist = new Set(DEFAULT_WHITELIST)
  if (extra) {
    for (const key of extra) {
      whitelist.add(key)
    }
  }
  return whitelist
}

export interface LogEntry {
  timestamp: string
  level: LogLevel
  message: string
  metadata?: Record<string, unknown>
  context?: Record<string, unknown>
  error?: unknown
}

export function createLogEntry(level: LogLevel, message: string, options?: LogOptions): LogEntry {
  const whitelist = buildWhitelist(options?.whitelist)

  const entry: LogEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
  }

  if (options?.metadata) {
    entry.metadata = sanitizeValue(options.metadata, whitelist) as Record<string, unknown>
  }

  if (options?.context) {
    entry.context = sanitizeValue(options.context, whitelist) as Record<string, unknown>
  }

  if (options?.error) {
    entry.error = sanitizeValue(options.error, whitelist)
  }

  return entry
}

function emitLog(entry: LogEntry) {
  const output = JSON.stringify(entry)
  if (entry.level === 'error' || entry.level === 'warn') {
    console.error(output)
  } else {
    console.log(output)
  }
}

function log(level: LogLevel, message: string, options?: LogOptions) {
  const entry = createLogEntry(level, message, options)
  emitLog(entry)
}

export const logger = {
  debug: (message: string, options?: LogOptions) => log('debug', message, options),
  info: (message: string, options?: LogOptions) => log('info', message, options),
  warn: (message: string, options?: LogOptions) => log('warn', message, options),
  error: (message: string, options?: LogOptions) => log('error', message, options),
}
