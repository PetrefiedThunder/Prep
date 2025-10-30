import { publishSampleEvent } from './integrationProducer.js';

publishSampleEvent().catch((error) => {
  console.error('Failed to publish sample event', error);
  process.exitCode = 1;
});
