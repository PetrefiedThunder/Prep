import Fastify from 'fastify';
import fastifyJwt from '@fastify/jwt';

const app = Fastify();
await app.register(fastifyJwt, { secret: 'test-secret-that-is-long-enough-for-validation-requirements' });
await app.ready();

console.log('app.jwt available?', typeof app.jwt !== 'undefined');

// Try to sign a token
const token = app.jwt.sign({ user: 'test' });
console.log('Token created via app.jwt.sign:', !!token);

await app.close();
