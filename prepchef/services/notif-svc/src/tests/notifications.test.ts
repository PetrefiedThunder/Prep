import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';

test('send notification', async () => {
  const app = await createApp();

  const res = await app.inject({
    method: 'POST',
    url: '/send',
    payload: {
      type: 'booking_confirmed',
      recipient_id: 'user-123',
      data: {
        booking_id: 'booking-456',
        kitchen_name: 'Test Kitchen'
      }
    }
  });

  assert.equal(res.statusCode, 202);
  const body = res.json();
  assert.ok(body.notification_id);
  assert.equal(body.status, 'queued');
  assert.equal(sentNotifications.length, 1);
  assert.equal(sentNotifications[0].recipient_id, 'user-123');
  await app.close();
});

