import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 50,
  duration: '2m',
  thresholds: {
    'http_req_duration{endpoint:booking}': ['p(95)<800'],
    'http_req_failed': ['rate<0.01'],
  },
};

const API = __ENV.API_BASE_URL;
const AUTH = `Bearer ${__ENV.SEED_ADMIN_TOKEN}`;

export default function () {
  const maker = http.get(`${API}/debug/random_maker`).json().maker_id;
  const kitchen = http.get(`${API}/debug/random_kitchen`).json().kitchen_id;

  const payload = JSON.stringify({
    maker_id: maker,
    kitchen_id: kitchen,
    start: '2025-11-05T10:00:00-08:00',
    end: '2025-11-05T11:00:00-08:00',
    deposit_cents: 10000,
    quote: { hourly_cents: 5500, hours: 1, cleaning_cents: 1000, platform_fee_bps: 1000 },
  });

  const params = { headers: { Authorization: AUTH, 'Content-Type': 'application/json' }, tags: { endpoint: 'booking' } };
  const res = http.post(`${API}/bookings`, payload, params);
  check(res, { 'booking 200/201': (r) => r.status === 200 || r.status === 201 });
  sleep(0.5);
}
