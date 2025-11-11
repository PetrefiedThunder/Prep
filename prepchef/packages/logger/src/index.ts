/**
 * Structured logging utility for PrepChef services
 *
 * Provides type-safe logging with structured metadata and correlation IDs.
 * In development, logs are human-readable. In production, logs are JSON formatted.
 */

interface LogMetadata {
  [key: string]: unknown;
}

interface LogContext {
  service?: string;
  environment?: string;
  correlationId?: string;
  [key: string]: unknown;
}

// Global context that can be set per request/operation
let globalContext: LogContext = {
  service: process.env.SERVICE_NAME || 'prep-service',
  environment: process.env.NODE_ENV || 'development',
};

/**
 * Set global logging context (e.g., service name, environment)
 */
export function setGlobalContext(context: LogContext): void {
  globalContext = { ...globalContext, ...context };
}

/**
 * Get current global context
 */
export function getGlobalContext(): Readonly<LogContext> {
  return { ...globalContext };
}

/**
 * Format log message with metadata
 */
function formatLog(level: string, message: string, meta?: LogMetadata): string {
  const isDevelopment = process.env.NODE_ENV === 'development';
  const timestamp = new Date().toISOString();

  const logData = {
    timestamp,
    level: level.toUpperCase(),
    message,
    ...globalContext,
    ...meta,
  };

  if (isDevelopment) {
    // Human-readable format for development
    const metaStr = Object.keys(meta || {}).length > 0
      ? ` ${JSON.stringify(meta)}`
      : '';
    return `[${timestamp}] [${level.toUpperCase()}] ${message}${metaStr}`;
  } else {
    // JSON format for production (compatible with log aggregation)
    return JSON.stringify(logData);
  }
}

/**
 * Type-safe structured logger
 */
export const log = {
  /**
   * Log debug-level message (verbose information for debugging)
   */
  debug(message: string, meta?: LogMetadata): void {
    if (process.env.LOG_LEVEL === 'debug') {
      console.debug(formatLog('debug', message, meta));
    }
  },

  /**
   * Log informational message
   */
  info(message: string, meta?: LogMetadata): void {
    console.log(formatLog('info', message, meta));
  },

  /**
   * Log warning message
   */
  warn(message: string, meta?: LogMetadata): void {
    console.warn(formatLog('warn', message, meta));
  },

  /**
   * Log error message with optional error object
   */
  error(message: string, error?: Error | unknown, meta?: LogMetadata): void {
    const errorMeta: LogMetadata = {};

    if (error instanceof Error) {
      errorMeta.error = {
        message: error.message,
        stack: error.stack,
        name: error.name,
      };
    } else if (error !== undefined) {
      errorMeta.error = error;
    }

    console.error(formatLog('error', message, { ...errorMeta, ...meta }));
  },
};

/**
 * Create a child logger with default metadata
 * Useful for adding context like request IDs, user IDs, etc.
 */
export function createChildLogger(defaultMeta: LogMetadata) {
  return {
    debug: (msg: string, meta?: LogMetadata) =>
      log.debug(msg, { ...defaultMeta, ...meta }),

    info: (msg: string, meta?: LogMetadata) =>
      log.info(msg, { ...defaultMeta, ...meta }),

    warn: (msg: string, meta?: LogMetadata) =>
      log.warn(msg, { ...defaultMeta, ...meta }),

    error: (msg: string, error?: Error | unknown, meta?: LogMetadata) =>
      log.error(msg, error, { ...defaultMeta, ...meta }),
  };
}

/**
 * Middleware helper to create request-scoped logger
 */
export function createRequestLogger(requestId: string, additionalMeta?: LogMetadata) {
  return createChildLogger({
    requestId,
    ...additionalMeta,
  });
}
