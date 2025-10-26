import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 50,
      duration: '5m',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.001'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const REQUESTS = [
  { name: 'compliance-query', method: 'GET', path: '/compliance/query' },
  { name: 'bookings', method: 'GET', path: '/bookings' },
  { name: 'analytics-host', method: 'GET', path: '/analytics/host/1' },
];

export default function smokeTest() {
  const responses = http.batch(
    REQUESTS.map(({ method, path, name }) => [method, `${BASE_URL}${path}`, null, { tags: { endpoint: name } }]),
  );

  responses.forEach((response, index) => {
    const { name } = REQUESTS[index];
    check(response, {
      [`${name} responded with status 2xx`]: (res) => res.status >= 200 && res.status < 300,
    });
  });
}
