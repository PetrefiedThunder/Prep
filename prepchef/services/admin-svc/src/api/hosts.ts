/**
 * Host Onboarding API (D13)
 * Endpoints for host profile creation, certificate uploads, and validation
 */

import { FastifyInstance } from 'fastify';
import '@fastify/multipart';
import { z } from 'zod';
import { Pool } from 'pg';
import { ApiError } from '@prep/common';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { randomUUID } from 'crypto';
import { log } from '@prep/logger';

const CreateHostSchema = z.object({
  name: z.string().min(1).max(255),
  email: z.string().email(),
  business_name: z.string().min(1).max(255),
  business_address: z.string().min(1),
  phone: z.string().min(10).max(20),
  tax_id: z.string().optional()
});

const UploadCertificateSchema = z.object({
  certificate_type: z.enum(['health_permit', 'food_handler', 'business_license', 'insurance']),
  expiration_date: z.string().datetime(),
  issuing_agency: z.string()
});

export default async function (app: FastifyInstance) {
  const db = new Pool({ connectionString: process.env.DATABASE_URL });

  // Initialize S3/MinIO client
  const s3 = new S3Client({
    endpoint: process.env.MINIO_ENDPOINT || 'http://minio:9000',
    region: 'us-east-1',
    credentials: {
      accessKeyId: process.env.MINIO_ACCESS_KEY || 'minioadmin',
      secretAccessKey: process.env.MINIO_SECRET_KEY || 'minioadmin'
    },
    forcePathStyle: true
  });

  /**
   * POST /api/hosts
   * Create a host profile
   */
  app.post('/api/hosts', async (req, reply) => {
    const parsed = CreateHostSchema.safeParse(req.body);

    if (!parsed.success) {
      return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid request body'));
    }

    const { name, email, business_name, business_address, phone, tax_id } = parsed.data;
    const hostId = randomUUID();

    try {
      // Check if email already exists
      const existing = await db.query('SELECT host_id FROM hosts WHERE email = $1', [email]);

      if (existing.rows.length > 0) {
        return reply.code(409).send(ApiError('PC-HOST-409', 'Host with this email already exists'));
      }

      // Create host profile
      const result = await db.query(
        `INSERT INTO hosts (
          host_id, name, email, business_name, business_address, phone, tax_id,
          status, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
        RETURNING *`,
        [hostId, name, email, business_name, business_address, phone, tax_id, 'pending']
      );

      log.info('Host profile created', { host_id: hostId, email });

      return reply.code(201).send({
        host_id: result.rows[0].host_id,
        name: result.rows[0].name,
        email: result.rows[0].email,
        status: result.rows[0].status
      });

    } catch (error) {
      log.error('Failed to create host', error);
      return reply.code(500).send(ApiError('PC-HOST-500', 'Failed to create host profile'));
    }
  });

  /**
   * POST /api/hosts/:id/certificates
   * Upload certificate document
   */
  app.post('/api/hosts/:id/certificates', async (req, reply) => {
    const { id: hostId } = req.params as { id: string };
    const data = await req.file();

    if (!data) {
      return reply.code(400).send(ApiError('PC-REQ-400', 'No file uploaded'));
    }

    const getFieldValue = (field: any) => {
      if (Array.isArray(field)) return field[0]?.value;
      return field?.value;
    };

    const parsed = UploadCertificateSchema.safeParse({
      certificate_type: getFieldValue(data.fields.certificate_type),
      expiration_date: getFieldValue(data.fields.expiration_date),
      issuing_agency: getFieldValue(data.fields.issuing_agency)
    });

    if (!parsed.success) {
      return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid certificate metadata'));
    }

    try {
      // Verify host exists
      const hostResult = await db.query('SELECT host_id FROM hosts WHERE host_id = $1', [hostId]);

      if (hostResult.rows.length === 0) {
        return reply.code(404).send(ApiError('PC-HOST-404', 'Host not found'));
      }

      // Upload file to S3/MinIO
      const certificateId = randomUUID();
      const fileKey = `certificates/${hostId}/${certificateId}.pdf`;

      const buffer = await data.toBuffer();

      await s3.send(new PutObjectCommand({
        Bucket: 'prepchef-certificates',
        Key: fileKey,
        Body: buffer,
        ContentType: data.mimetype
      }));

      // Store certificate metadata in database
      const { certificate_type, expiration_date, issuing_agency } = parsed.data;

      await db.query(
        `INSERT INTO certificates (
          certificate_id, host_id, certificate_type, document_url,
          expiration_date, issuing_agency, status, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())`,
        [
          certificateId,
          hostId,
          certificate_type,
          fileKey,
          expiration_date,
          issuing_agency,
          'pending_validation'
        ]
      );

      log.info('Certificate uploaded', { host_id: hostId, certificate_id: certificateId });

      return reply.code(201).send({
        certificate_id: certificateId,
        certificate_type,
        status: 'pending_validation',
        document_url: fileKey
      });

    } catch (error) {
      log.error('Failed to upload certificate', error);
      return reply.code(500).send(ApiError('PC-CERT-500', 'Failed to upload certificate'));
    }
  });

  /**
   * POST /api/hosts/:id/validate
   * Trigger compliance validation
   */
  app.post('/api/hosts/:id/validate', async (req, reply) => {
    const { id: hostId } = req.params as { id: string };

    try {
      // Get all certificates for host
      const certsResult = await db.query(
        `SELECT certificate_id, certificate_type, document_url, expiration_date, issuing_agency
         FROM certificates
         WHERE host_id = $1 AND status = 'pending_validation'`,
        [hostId]
      );

      if (certsResult.rows.length === 0) {
        return reply.code(400).send(ApiError('PC-CERT-400', 'No certificates to validate'));
      }

      // Call ComplianceEngine for each certificate
      const validationResults = [];

      for (const cert of certsResult.rows) {
        // In production, this would call the Python compliance service
        // For now, simulate validation
        const validation = {
          certificate_id: cert.certificate_id,
          certificate_type: cert.certificate_type,
          violations: [],
          severity: 'none',
          pass: true,
          confidence: 0.95,
          expiration_check: new Date(cert.expiration_date) > new Date()
        };

        // Update certificate status
        await db.query(
          `UPDATE certificates
           SET status = $1, validation_result = $2, validated_at = NOW()
           WHERE certificate_id = $3`,
          [
            validation.pass ? 'validated' : 'rejected',
            JSON.stringify(validation),
            cert.certificate_id
          ]
        );

        validationResults.push(validation);
      }

      // Update host status if all certificates valid
      const allValid = validationResults.every(v => v.pass);

      if (allValid) {
        await db.query(
          `UPDATE hosts SET status = 'validated', validated_at = NOW() WHERE host_id = $1`,
          [hostId]
        );
      }

      log.info('Host validation completed', { host_id: hostId, all_valid: allValid });

      return reply.code(200).send({
        host_id: hostId,
        status: allValid ? 'validated' : 'validation_failed',
        certificates: validationResults
      });

    } catch (error) {
      log.error('Validation failed', error);
      return reply.code(500).send(ApiError('PC-VAL-500', 'Validation failed'));
    }
  });

  /**
   * GET /api/hosts/:id
   * Get host profile with certificates
   */
  app.get('/api/hosts/:id', async (req, reply) => {
    const { id: hostId } = req.params as { id: string };

    try {
      const hostResult = await db.query('SELECT * FROM hosts WHERE host_id = $1', [hostId]);

      if (hostResult.rows.length === 0) {
        return reply.code(404).send(ApiError('PC-HOST-404', 'Host not found'));
      }

      const certsResult = await db.query(
        'SELECT * FROM certificates WHERE host_id = $1 ORDER BY created_at DESC',
        [hostId]
      );

      return reply.code(200).send({
        ...hostResult.rows[0],
        certificates: certsResult.rows
      });

    } catch (error) {
      log.error('Failed to get host', error);
      return reply.code(500).send(ApiError('PC-HOST-500', 'Failed to retrieve host'));
    }
  });

  app.addHook('onClose', async () => {
    await db.end();
  });
}
