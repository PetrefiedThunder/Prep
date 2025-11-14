import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';

const sampleNotification = {
  type: 'booking_confirmed',
  title: 'Booking confirmed',
  body: 'Your booking has been confirmed',
  recipient_id: 'user-123',
  data: {
    booking_id: 'booking-456'
  }
};

test('send notification queues channels and stores record', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/api/v1/notifications/send',
    payload: sampleNotification
  });

  assert.equal(res.statusCode, 202);
  const body = res.json();
  assert.ok(body.notification_id);
  assert.equal(body.status, 'queued');
  assert.deepEqual(body.channels.sort(), ['email', 'in_app', 'push']);

  const context = app.notificationContext;
  const stored = await context.repository.listForUser('user-123');
  assert.equal(stored.length, 1);
  assert.equal(stored[0].type, 'booking_confirmed');
  assert.equal(stored[0].emailSent, true);
  assert.equal(stored[0].pushSent, true);

  const emails = context.emailProvider.getSentEmails();
  assert.equal(emails.length, 1);
  assert.equal(emails[0].to, 'user-123');
  assert.equal(emails[0].subject, 'Booking confirmed');

  const smsMessages = context.smsProvider.getSentMessages();
  assert.equal(smsMessages.length, 0);

  await app.close();
});

test('respects user notification preferences when sending', async () => {
  const app = await createApp();
  const token = await app.jwt.sign({ sub: 'user-abc', email: 'user@example.com' });

  const updateRes = await app.inject({
    method: 'PUT',
    url: '/api/v1/notifications/preferences',
    payload: {
      email: false,
      sms: true,
      in_app: true,
      push: false
    },
    headers: {
      authorization: `Bearer ${token}`
    }
  });

  assert.equal(updateRes.statusCode, 200);
  const updateBody = updateRes.json();
  assert.equal(updateBody.preferences.email, false);
  assert.equal(updateBody.preferences.sms, true);

  const sendRes = await app.inject({
    method: 'POST',
    url: '/api/v1/notifications/send',
    payload: {
      ...sampleNotification,
      recipient_id: 'user-abc',
      title: 'Moderation update'
    }
  });

  assert.equal(sendRes.statusCode, 202);
  const sendBody = sendRes.json();
  assert.deepEqual(sendBody.channels.sort(), ['in_app', 'sms']);

  const emails = app.notificationContext.emailProvider.getSentEmails();
  assert.equal(emails.length, 0);

  const smsMessages = app.notificationContext.smsProvider.getSentMessages();
  assert.equal(smsMessages.length, 1);
  assert.equal(smsMessages[0].to, 'user-abc');

  await app.close();
});
