import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';

test('send notification', async () => {
  const app = Fastify();
  
  const sentNotifications: any[] = [];
  
  app.post('/send', async (req, reply) => {
    const { type, recipient_id, data } = req.body as any;
    
    if (!type || !recipient_id) {
      return reply.code(400).send({
        error: 'Missing required fields',
        message: 'type and recipient_id are required'
      });
    }
    
    const notification = {
      id: crypto.randomUUID(),
      type,
      recipient_id,
      data: data || {},
      sent_at: new Date().toISOString(),
      channels: ['email', 'push']
    };
    
    sentNotifications.push(notification);
    
    return reply.code(202).send({
      notification_id: notification.id,
      status: 'queued'
    });
  });
  
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
});

