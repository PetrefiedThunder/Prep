import Fastify from 'fastify';
import cors from 'fastify-cors';
import { log } from '@prep/logger';
import auth from './api/auth';

const app = Fastify({ logger: false });
app.register(cors);

app.get('/healthz', async () => ({ ok: true, svc: 'auth-svc' }));

app.register(async function routes(instance) {
  instance.get('/', async () => ({ name: 'auth-svc' }));
});

const port = Number(process.env.PORT || 0) || (Math.floor(Math.random()*1000)+3000);
app.register(auth);
app.listen({ port }).then(() => log.info('auth-svc listening', port));
