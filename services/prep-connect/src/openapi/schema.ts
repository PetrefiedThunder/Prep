import type { SchemaObject } from 'openapi3-ts/oas30';
import { OpenApiBuilder } from 'openapi3-ts/oas30';

const integrationSchema: SchemaObject = {
  type: 'object',
  required: [
    'id',
    'userId',
    'serviceType',
    'vendorName',
    'authMethod',
    'syncFrequency',
    'status',
    'metadata',
    'createdAt',
    'updatedAt',
  ],
  properties: {
    id: { type: 'string', format: 'uuid' },
    userId: { type: 'string', format: 'uuid' },
    kitchenId: { type: 'string', format: 'uuid', nullable: true },
    serviceType: { type: 'string' },
    vendorName: { type: 'string' },
    authMethod: { type: 'string' },
    syncFrequency: { type: 'string' },
    status: { type: 'string', enum: ['active', 'inactive', 'error', 'pending'] },
    metadata: { type: 'object', additionalProperties: true },
    createdAt: { type: 'string', format: 'date-time' },
    updatedAt: { type: 'string', format: 'date-time' },
  },
};

const integrationInputSchema: SchemaObject = {
  type: 'object',
  required: ['serviceType', 'vendorName', 'authMethod', 'syncFrequency'],
  properties: {
    serviceType: { type: 'string' },
    vendorName: { type: 'string' },
    authMethod: { type: 'string' },
    syncFrequency: { type: 'string' },
    status: { type: 'string', enum: ['active', 'inactive', 'error', 'pending'] },
    kitchenId: { type: 'string', format: 'uuid', nullable: true },
    metadata: { type: 'object', additionalProperties: true },
  },
};

export function buildOpenApiSchema() {
  const builder = new OpenApiBuilder();
  builder.addInfo({
    title: 'Prep Connect API',
    version: '0.1.0',
    description: 'Internal service for managing third-party integrations.',
  });
  builder.addServer({ url: 'https://api.prep.test/connect' });

  builder.addPath('/integrations', {
    get: {
      summary: 'List integrations for the authenticated user',
      responses: {
        200: {
          description: 'A list of integrations',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  data: {
                    type: 'array',
                    items: { $ref: '#/components/schemas/Integration' },
                  },
                },
              },
            },
          },
        },
      },
      security: [{ bearerAuth: [] }],
    },
    post: {
      summary: 'Create a new integration',
      requestBody: {
        required: true,
        content: {
          'application/json': {
            schema: { $ref: '#/components/schemas/IntegrationInput' },
          },
        },
      },
      responses: {
        201: {
          description: 'Integration created',
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/Integration' },
            },
          },
        },
      },
      security: [{ bearerAuth: [] }],
    },
  });

  builder.addPath('/integrations/{integrationId}', {
    patch: {
      summary: 'Update an integration',
      parameters: [
        {
          name: 'integrationId',
          in: 'path',
          required: true,
          schema: { type: 'string', format: 'uuid' },
        },
      ],
      requestBody: {
        required: true,
        content: {
          'application/json': {
            schema: { $ref: '#/components/schemas/IntegrationInput' },
          },
        },
      },
      responses: {
        200: {
          description: 'Updated integration',
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/Integration' },
            },
          },
        },
      },
      security: [{ bearerAuth: [] }],
    },
    delete: {
      summary: 'Delete an integration',
      parameters: [
        {
          name: 'integrationId',
          in: 'path',
          required: true,
          schema: { type: 'string', format: 'uuid' },
        },
      ],
      responses: {
        204: { description: 'Integration deleted' },
        404: { description: 'Integration not found' },
      },
      security: [{ bearerAuth: [] }],
    },
  });

  builder.addSchema('Integration', integrationSchema);
  builder.addSchema('IntegrationInput', integrationInputSchema);
  builder.addSecurityScheme('bearerAuth', {
    type: 'http',
    scheme: 'bearer',
    bearerFormat: 'JWT',
  });

  return builder.getSpec();
}
