import { test } from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import WebSocket from 'ws';
import type { AddressInfo } from 'node:net';
import { createApp } from '../index';

async function waitFor<T>(source: () => T | undefined, timeoutMs = 1000): Promise<T> {
  const start = Date.now();
  return new Promise<T>((resolve, reject) => {
    const check = () => {
      const value = source();
      if (value !== undefined) {
        resolve(value);
        return;
      }
      if (Date.now() - start > timeoutMs) {
        reject(new Error('Timed out waiting for message'));
        return;
      }
      setTimeout(check, 10);
    };
    check();
  });
}

test('websocket clients receive real-time notifications', async () => {
  const app = await createApp();
  await app.listen({ port: 0 });
  const { port } = app.server.address() as AddressInfo;
  const token = await app.jwt.sign({ sub: 'user-realtime', email: 'ws@prep.dev' });

  const ws = new WebSocket(`ws://127.0.0.1:${port}/ws?token=${token}`);
  const messages: any[] = [];
  ws.on('message', data => {
    messages.push(JSON.parse(data.toString()));
  });

  await once(ws, 'open');
  await waitFor(() => messages.find(msg => msg.type === 'connected'));

  await app.inject({
    method: 'POST',
    url: '/api/v1/notifications/send',
    payload: {
      type: 'message_new',
      title: 'New message',
      body: 'You have a new message from a host',
      recipient_id: 'user-realtime'
    }
  });

  const notificationMessage = await waitFor(
    () => messages.find(msg => msg.type === 'notification')
  );

  assert.equal(notificationMessage.notification.type, 'message_new');
  assert.equal(notificationMessage.notification.userId, 'user-realtime');

  ws.close();
  await once(ws, 'close');
  await app.close();
});
