const swaggerJsdoc = require('swagger-jsdoc');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Nigerian Languages API',
      version: '1.0.0',
      description:
        'A dialect-aware linguistic repository REST API for Nigerian languages. ' +
        'Browse languages, dialects, and dictionary entries. ' +
        'Protected write endpoints require an `x-api-key` header.',
    },
    servers: [{ url: '/api' }],
    components: {
      securitySchemes: {
        ApiKeyAuth: {
          type: 'apiKey',
          in: 'header',
          name: 'x-api-key',
        },
      },
      schemas: {
        Language: {
          type: 'object',
          properties: {
            language_id: { type: 'integer', example: 1 },
            name: { type: 'string', example: 'Yoruba' },
            iso_code: { type: 'string', example: 'yor' },
          },
        },
        Dialect: {
          type: 'object',
          properties: {
            dialect_id: { type: 'integer', example: 3 },
            language_id: { type: 'integer', example: 1 },
            name: { type: 'string', example: 'Ekiti Yoruba' },
          },
        },
        Entry: {
          type: 'object',
          properties: {
            entry_id: { type: 'integer', example: 42 },
            headword: { type: 'string', example: 'omi' },
            pos: { type: 'string', nullable: true, example: 'noun' },
            dialect_id: { type: 'integer', example: 3 },
            dialect_name: { type: 'string', example: 'Ekiti Yoruba' },
            language_name: { type: 'string', example: 'Yoruba' },
          },
        },
        EntryWithMetadata: {
          allOf: [
            { $ref: '#/components/schemas/Entry' },
            {
              type: 'object',
              properties: {
                metadata: {
                  type: 'object',
                  nullable: true,
                  example: { definition: 'water', tone: 'LH' },
                },
              },
            },
          ],
        },
        Error: {
          type: 'object',
          properties: {
            error: { type: 'string', example: 'Entry not found' },
          },
        },
      },
    },
  },
  // Scan all route files and app.js for @swagger JSDoc comments
  apis: ['./src/routes/*.js', './src/app.js'],
};

module.exports = swaggerJsdoc(options);
