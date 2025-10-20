import { test } from 'node:test';
import { MockAgent, setGlobalDispatcher } from 'undici';
import { strict as assert } from 'node:assert';
import { createApp } from '../index';

test('creates booking on success', async () => {
  const agent = new MockAgent();
  agent.disableNetConnect();
  setGlobalDispatcher(agent);
  agent.get('http://compliance').intercept({ path: '/check', method: 'POST' }).reply(204, {});
  agent.get('http://availability').intercept({ path: '/check', method: 'POST' }).reply(204, {});
  agent.get('http://pricing').intercept({ path: '/quote', method: 'POST' }).reply(200, { amount: 100 });
  agent.get('http://payments').intercept({ path: '/intents', method: 'POST' }).reply(200, { id: 'pi_123' });

  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/bookings',
    payload: {
      listing_id: '00000000-0000-0000-0000-000000000001',
      starts_at: '2020-01-01',
      ends_at: '2020-01-02'
    }
  });
  assert.equal(res.statusCode, 201);
  assert.equal(res.json().payment_intent_id, 'pi_123');
  await app.close();
  await agent.close();
});

test('maps compliance failure', async () => {
  const agent = new MockAgent();
  agent.disableNetConnect();
  setGlobalDispatcher(agent);
  agent.get('http://compliance').intercept({ path: '/check', method: 'POST' }).reply(412, {});

  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/bookings',
    payload: {
      listing_id: '00000000-0000-0000-0000-000000000001',
      starts_at: '2020-01-01',
      ends_at: '2020-01-02'
    }
  });
  assert.equal(res.statusCode, 412);
  assert.equal(res.json().code, 'PC-COMP-412');
  await app.close();
  await agent.close();
});

test('maps availability failure', async () => {
  const agent = new MockAgent();
  agent.disableNetConnect();
  setGlobalDispatcher(agent);
  agent.get('http://compliance').intercept({ path: '/check', method: 'POST' }).reply(204, {});
  agent.get('http://availability').intercept({ path: '/check', method: 'POST' }).reply(412, {});

  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/bookings',
    payload: {
      listing_id: '00000000-0000-0000-0000-000000000001',
      starts_at: '2020-01-01',
      ends_at: '2020-01-02'
    }
  });
  assert.equal(res.statusCode, 412);
  assert.equal(res.json().code, 'PC-AVAIL-412');
  await app.close();
  await agent.close();
});

test('maps pricing failure', async () => {
  const agent = new MockAgent();
  agent.disableNetConnect();
  setGlobalDispatcher(agent);
  agent.get('http://compliance').intercept({ path: '/check', method: 'POST' }).reply(204, {});
  agent.get('http://availability').intercept({ path: '/check', method: 'POST' }).reply(204, {});
  agent.get('http://pricing').intercept({ path: '/quote', method: 'POST' }).reply(412, {});

  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/bookings',
    payload: {
      listing_id: '00000000-0000-0000-0000-000000000001',
      starts_at: '2020-01-01',
      ends_at: '2020-01-02'
    }
  });
  assert.equal(res.statusCode, 412);
  assert.equal(res.json().code, 'PC-PRICE-412');
  await app.close();
  await agent.close();
});

test('maps payment failure', async () => {
  const agent = new MockAgent();
  agent.disableNetConnect();
  setGlobalDispatcher(agent);
  agent.get('http://compliance').intercept({ path: '/check', method: 'POST' }).reply(204, {});
  agent.get('http://availability').intercept({ path: '/check', method: 'POST' }).reply(204, {});
  agent.get('http://pricing').intercept({ path: '/quote', method: 'POST' }).reply(200, { amount: 100 });
  agent.get('http://payments').intercept({ path: '/intents', method: 'POST' }).reply(402, {});

  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/bookings',
    payload: {
      listing_id: '00000000-0000-0000-0000-000000000001',
      starts_at: '2020-01-01',
      ends_at: '2020-01-02'
    }
  });
  assert.equal(res.statusCode, 402);
  assert.equal(res.json().code, 'PC-PAY-402');
  await app.close();
  await agent.close();
});

