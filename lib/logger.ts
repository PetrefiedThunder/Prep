const SENSITIVE_KEYS = ['token', 'secret', 'key', 'password', 'authorization', 'cookie']

function shouldRedact(key: string) {
  return SENSITIVE_KEYS.some((sensitive) => key.toLowerCase().includes(sensitive))
}

function sanitizeContext(context?: Record<string, unknown>) {
  if (!context) return undefined

  return Object.entries(context).reduce<Record<string, unknown>>((acc, [key, value]) => {
    if (value === undefined) return acc

    if (shouldRedact(key)) {
      acc[key] = '[redacted]'
      return acc
    }

    if (typeof value === 'string') {
      acc[key] = value
    } else if (value instanceof Error) {
      acc[key] = value.message
    } else {
      acc[key] = value
    }

    return acc
  }, {})
}

export function logInfo(message: string, context?: Record<string, unknown>) {
  const sanitized = sanitizeContext(context)
  if (sanitized) {
    console.info(message, sanitized)
  } else {
    console.info(message)
  }
}

export function logError(message: string, context?: Record<string, unknown>) {
  const sanitized = sanitizeContext(context)
  if (sanitized) {
    console.error(message, sanitized)
  } else {
    console.error(message)
  }
}

export function maskIdentifier(value: string | null | undefined, visible = 6) {
  if (!value) return '[redacted]'
  const trimmed = value.toString()
  if (trimmed.length <= visible) return '[redacted]'
  return `${trimmed.slice(0, visible)}…[redacted]`
}
