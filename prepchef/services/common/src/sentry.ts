/**
 * Sentry Integration (G23)
 * Error tracking with contextual tags
 */

import * as Sentry from '@sentry/node';
import { FastifyInstance, FastifyRequest } from 'fastify';

export interface SentryConfig {
  dsn?: string;
  environment: string;
  serviceName: string;
  enabled: boolean;
  sampleRate?: number;
  tracesSampleRate?: number;
}

export function initializeSentry(config: SentryConfig) {
  if (!config.enabled || !config.dsn) {
    console.log('Sentry disabled');
    return;
  }

  Sentry.init({
    dsn: config.dsn,
    environment: config.environment,
    serverName: config.serviceName,
    sampleRate: config.sampleRate || 1.0,
    tracesSampleRate: config.tracesSampleRate || 0.1,
    integrations: [
      // Add performance monitoring
      new Sentry.Integrations.Http({ tracing: true })
    ],
    beforeSend(event, hint) {
      // Filter out expected errors
      if (event.exception) {
        const error = hint.originalException as Error;
        if (error?.message?.includes('ECONNREFUSED')) {
          return null; // Don't send connection errors
        }
      }
      return event;
    }
  });

  console.log(`Sentry initialized for ${config.serviceName} in ${config.environment}`);
}

export function registerSentryHandlers(app: FastifyInstance, serviceName: string) {
  // Request handler to add context
  app.addHook('onRequest', async (request, reply) => {
    Sentry.configureScope((scope) => {
      scope.setTag('service', serviceName);
      scope.setTag('method', request.method);
      scope.setTag('route', request.url);

      // Add user context if authenticated
      if (request.user) {
        scope.setUser({
          id: (request.user as any).user_id,
          email: (request.user as any).email
        });
      }
    });
  });

  // Error handler to capture exceptions
  app.setErrorHandler((error, request, reply) => {
    // Add request context
    Sentry.withScope((scope) => {
      scope.setTag('service', serviceName);
      scope.setContext('request', {
        method: request.method,
        url: request.url,
        params: request.params,
        query: request.query,
        headers: request.headers,
        body: request.body
      });

      // Capture error
      Sentry.captureException(error);
    });

    // Send error response
    reply.status(500).send({
      error: 'Internal Server Error',
      message: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  });
}

/**
 * Capture error with custom context
 */
export function captureError(
  error: Error,
  context?: {
    booking_id?: string;
    user_id?: string;
    payment_intent_id?: string;
    [key: string]: any;
  }
) {
  Sentry.withScope((scope) => {
    if (context) {
      // Add tags for easy filtering
      if (context.booking_id) scope.setTag('booking_id', context.booking_id);
      if (context.user_id) scope.setTag('user_id', context.user_id);
      if (context.payment_intent_id) scope.setTag('payment_intent_id', context.payment_intent_id);

      // Add full context
      scope.setContext('custom', context);
    }

    Sentry.captureException(error);
  });
}

/**
 * Capture message (non-error event)
 */
export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info', context?: any) {
  Sentry.withScope((scope) => {
    if (context) {
      scope.setContext('custom', context);
    }

    Sentry.captureMessage(message, level);
  });
}

// Export Sentry for direct usage
export { Sentry };
