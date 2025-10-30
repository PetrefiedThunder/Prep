import { Kafka, logLevel } from 'kafkajs';

export class IntegrationEventProducer {
  constructor({ clientId = 'prep-connect', brokers, topic = 'integration_events' }) {
    if (!brokers || brokers.length === 0) {
      throw new Error('Kafka brokers must be provided to IntegrationEventProducer');
    }
    this.topic = topic;
    this.kafka = new Kafka({ clientId, brokers, logLevel: logLevel.INFO });
    this.producer = this.kafka.producer();
  }

  async connect() {
    await this.producer.connect();
  }

  async disconnect() {
    await this.producer.disconnect();
  }

  async publishStatus({ id, name, status = 'online', payload = {}, source = 'prep-connect-service' }) {
    if (!id || !name) {
      throw new Error('Integration status events require both id and name');
    }
    const event = {
      integrationId: id,
      integrationName: name,
      source,
      eventType: 'status',
      status,
      payload,
      occurred_at: new Date().toISOString(),
    };
    await this.producer.send({
      topic: this.topic,
      messages: [{ value: JSON.stringify(event) }],
    });
    return event;
  }
}

export async function publishSampleEvent() {
  const brokers = (process.env.KAFKA_BROKERS || 'localhost:9092').split(',');
  const producer = new IntegrationEventProducer({ brokers });
  await producer.connect();
  try {
    const payload = {
      connected: true,
      health: 'healthy',
      auth_status: 'connected',
      last_sync_at: new Date().toISOString(),
    };
    const event = await producer.publishStatus({
      id: 'sample-crm',
      name: 'Sample CRM',
      status: 'online',
      payload,
    });
    console.log('Published sample integration event', event);
  } finally {
    await producer.disconnect();
  }
}
