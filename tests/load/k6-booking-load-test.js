/**
 * Load Test Scenarios (F22)
 * k6 load test simulating 200 concurrent users performing availability checks and booking attempts
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const bookingSuccessRate = new Rate('booking_success');
const availabilityCheckLatency = new Trend('availability_check_latency');
const bookingAttempts = new Counter('booking_attempts');
const raceConditionDetected = new Counter('race_conditions_detected');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp up to 50 users
    { duration: '1m', target: 100 },   // Ramp up to 100 users
    { duration: '2m', target: 200 },   // Peak load: 200 users
    { duration: '1m', target: 100 },   // Ramp down
    { duration: '30s', target: 0 },    // Cool down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'], // 95% of requests < 500ms
    'http_req_failed': ['rate<0.01'],                  // < 1% failure rate
    'booking_success': ['rate>0.7'],                   // > 70% booking success
    'race_conditions_detected': ['count<10'],          // < 10 race conditions
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';

// Test data
const KITCHEN_ID = '11111111-1111-1111-1111-111111111111';
const USER_POOL_SIZE = 500;

// Generate user IDs
function generateUserId() {
  const array = new Uint32Array(1);
  crypto.getRandomValues(array);
  const userId = array[0] % USER_POOL_SIZE;
  return `22222222-2222-2222-2222-${userId.toString().padStart(12, '0')}`;
}

// Generate booking times (tomorrow, various slots)
function generateBookingTime() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const timeSlotArray = new Uint32Array(1);
  crypto.getRandomValues(timeSlotArray);
  const randomSlot = timeSlotArray[0] % 8;
  tomorrow.setHours(9 + randomSlot, 0, 0, 0); // 9 AM - 5 PM

  const startTime = tomorrow.toISOString();

  const endTime = new Date(tomorrow);
  endTime.setHours(endTime.getHours() + 2); // 2-hour bookings

  return {
    start_time: startTime,
    end_time: endTime.toISOString()
  };
}

export default function () {
  const userId = generateUserId();

  group('Availability Check', () => {
    const { start_time, end_time } = generateBookingTime();

    // Check availability
    const checkStart = Date.now();
    const availabilityRes = http.get(
      `${BASE_URL}/api/availability/check?kitchen_id=${KITCHEN_ID}&start=${start_time}&end=${end_time}`
    );

    const checkLatency = Date.now() - checkStart;
    availabilityCheckLatency.add(checkLatency);

    check(availabilityRes, {
      'availability check status 200': (r) => r.status === 200,
      'availability check < 200ms': () => checkLatency < 200,
    });

    const available = availabilityRes.json('available');

    // If available, attempt to book
    if (available) {
      group('Create Booking', () => {
        bookingAttempts.add(1);

        const bookingPayload = JSON.stringify({
          kitchen_id: KITCHEN_ID,
          user_id: userId,
          start_time,
          end_time
        });

        const bookingRes = http.post(
          `${BASE_URL}/api/bookings`,
          bookingPayload,
          {
            headers: { 'Content-Type': 'application/json' },
          }
        );

        const bookingSuccess = check(bookingRes, {
          'booking created': (r) => r.status === 201,
          'booking conflict handled': (r) => r.status === 409,
        });

        // Track success rate
        bookingSuccessRate.add(bookingRes.status === 201);

        // Detect race condition (409 when availability said it was available)
        if (bookingRes.status === 409) {
          raceConditionDetected.add(1);
          console.log(`Race condition detected for user ${userId} at ${start_time}`);
        }

        // Verify response structure
        if (bookingRes.status === 201) {
          const booking = bookingRes.json();
          check(booking, {
            'has booking_id': (b) => b.booking_id !== undefined,
            'status is pending': (b) => b.status === 'pending',
          });
        }
      });
    }
  });

  // Simulate user think time
  sleep(Math.random() * 3 + 1); // 1-4 seconds
}

// Setup function (runs once)
export function setup() {
  console.log('Setting up load test...');

  // Create test kitchen if it doesn't exist
  const kitchenPayload = JSON.stringify({
    kitchen_id: KITCHEN_ID,
    name: 'Load Test Kitchen',
    address: '123 Test St'
  });

  const createKitchenRes = http.post(
    `${BASE_URL}/api/kitchens`,
    kitchenPayload,
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );

  console.log(`Kitchen setup status: ${createKitchenRes.status}`);

  return { kitchen_id: KITCHEN_ID };
}

// Teardown function (runs once)
export function teardown(data) {
  console.log('Tearing down load test...');
  console.log(`Kitchen ID: ${data.kitchen_id}`);

  // Optional: Clean up test bookings
  // (In production, you'd delete test data here)
}

/**
 * How to run this load test:
 *
 * 1. Install k6:
 *    brew install k6  # macOS
 *    # or download from https://k6.io
 *
 * 2. Ensure services are running:
 *    docker-compose up -d
 *
 * 3. Run the test:
 *    k6 run tests/load/k6-booking-load-test.js
 *
 * 4. With custom target:
 *    k6 run --vus 100 --duration 2m tests/load/k6-booking-load-test.js
 *
 * 5. Output results to JSON:
 *    k6 run --out json=results.json tests/load/k6-booking-load-test.js
 */
