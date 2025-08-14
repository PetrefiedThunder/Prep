import Fastify from 'fastify';
import cors from '@fastify/cors';
import { log } from '@prep/logger';

const app = Fastify({ logger: false });
app.register(cors);

app.get('/healthz', async () => ({ ok: true, svc: 'compliance-svc' }));

app.register(async function routes(instance) {
  instance.get('/', async () => ({ name: 'compliance-svc' }));
});

const port = Number(process.env.PORT || 0) || (Math.floor(Math.random()*1000)+3000);
app.listen({ port }).then(() => log.info('compliance-svc listening', port));
