/**
 * Prometheus Metrics (G24)
 * Exports request_count, request_latency_seconds, booking_success_count, compliance_validations_total
 */

import { FastifyInstance } from 'fastify';
import client from 'prom-client';

// Create a Registry
const register = new client.Registry();

// Add default metrics (CPU, memory, etc.)
client.collectDefaultMetrics({ register, prefix: 'prepchef_' });

// Custom metrics
const httpRequestsTotal = new client.Counter({
  name: 'prepchef_http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code', 'service'],
  registers: [register]
});

const httpRequestDuration = new client.Histogram({
  name: 'prepchef_http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code', 'service'],
  buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5],
  registers: [register]
});

const bookingSuccessCounter = new client.Counter({
  name: 'prepchef_booking_success_total',
  help: 'Total number of successful bookings created',
  labelNames: ['kitchen_id', 'status'],
  registers: [register]
});

const complianceValidationsTotal = new client.Counter({
  name: 'prepchef_compliance_validations_total',
  help: 'Total number of compliance validations performed',
  labelNames: ['certificate_type', 'result'],
  registers: [register]
});

const paymentIntentsTotal = new client.Counter({
  name: 'prepchef_payment_intents_total',
  help: 'Total number of payment intents created',
  labelNames: ['status'],
  registers: [register]
});

const activeSessions = new client.Gauge({
  name: 'prepchef_active_sessions',
  help: 'Number of active user sessions',
  registers: [register]
});

const databaseConnections = new client.Gauge({
  name: 'prepchef_database_connections',
  help: 'Number of active database connections',
  labelNames: ['state'],
  registers: [register]
});

/**
 * Register Prometheus metrics middleware
 */
export function registerPrometheusMetrics(app: FastifyInstance, serviceName: string) {
  // Request timing middleware
  app.addHook('onRequest', async (request, reply) => {
    (request as any).startTime = Date.now();
  });

  app.addHook('onResponse', async (request, reply) => {
    const duration = (Date.now() - (request as any).startTime) / 1000;
    const route = request.routerPath || request.url;

    httpRequestsTotal.inc({
      method: request.method,
      route,
      status_code: reply.statusCode,
      service: serviceName
    });

    httpRequestDuration.observe(
      {
        method: request.method,
        route,
        status_code: reply.statusCode,
        service: serviceName
      },
      duration
    );
  });

  // Metrics endpoint
  app.get('/metrics', async (request, reply) => {
    reply.type('text/plain');
    return await register.metrics();
  });
}

/**
 * Track successful booking
 */
export function trackBookingSuccess(kitchenId: string, status: string) {
  bookingSuccessCounter.inc({
    kitchen_id: kitchenId,
    status
  });
}

/**
 * Track compliance validation
 */
export function trackComplianceValidation(certificateType: string, result: 'pass' | 'fail') {
  complianceValidationsTotal.inc({
    certificate_type: certificateType,
    result
  });
}

/**
 * Track payment intent
 */
export function trackPaymentIntent(status: string) {
  paymentIntentsTotal.inc({ status });
}

/**
 * Update active sessions count
 */
export function setActiveSessions(count: number) {
  activeSessions.set(count);
}

/**
 * Update database connection metrics
 */
export function setDatabaseConnections(active: number, idle: number) {
  databaseConnections.set({ state: 'active' }, active);
  databaseConnections.set({ state: 'idle' }, idle);
}

export {
  register,
  httpRequestsTotal,
  httpRequestDuration,
  bookingSuccessCounter,
  complianceValidationsTotal,
  paymentIntentsTotal
};
