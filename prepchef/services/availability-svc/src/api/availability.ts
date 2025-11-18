import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';
import { AvailabilityService } from '../services/AvailabilityService';
import { getPrismaClient } from '@prep/database';

const CreateAvailabilityWindowSchema = z.object({
  listing_id: z.string().uuid(),
  day_of_week: z.number().int().min(0).max(6).optional(), // 0 = Sunday, 6 = Saturday
  start_time: z.string().regex(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/), // HH:MM format
  end_time: z.string().regex(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/), // HH:MM format
  start_date: z.string().datetime().optional().transform(val => val ? new Date(val) : undefined),
  end_date: z.string().datetime().optional().transform(val => val ? new Date(val) : undefined),
  is_recurring: z.boolean().default(true)
});

const GetAvailableSlotsSchema = z.object({
  start_date: z.string().datetime().transform(val => new Date(val)),
  end_date: z.string().datetime().transform(val => new Date(val))
});

export default async function (app: FastifyInstance) {
  const prisma = getPrismaClient();
  const availabilityService = new AvailabilityService(prisma);

  // Get availability windows for a listing
  app.get('/api/availability/:listingId/windows', async (req, reply) => {
    const { listingId } = req.params as { listingId: string };

    try {
      const windows = await availabilityService.getAvailabilityWindows(listingId);

      return reply.code(200).send({
        listing_id: listingId,
        windows: windows.map(w => ({
          id: w.id,
          listing_id: w.listingId,
          day_of_week: w.dayOfWeek,
          start_time: w.startTime.toISOString(),
          end_time: w.endTime.toISOString(),
          start_date: w.startDate?.toISOString(),
          end_date: w.endDate?.toISOString(),
          is_recurring: w.isRecurring,
          created_at: w.createdAt.toISOString()
        }))
      });
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send(ApiError('PC-AVAIL-500', 'Unexpected error'));
    }
  });

  // Get available time slots for a listing
  app.get('/api/availability/:listingId/slots', async (req, reply) => {
    const { listingId } = req.params as { listingId: string };

    try {
      const query = GetAvailableSlotsSchema.parse(req.query);

      const slots = await availabilityService.getAvailableSlots(
        listingId,
        query.start_date,
        query.end_date
      );

      return reply.code(200).send({
        listing_id: listingId,
        start_date: query.start_date.toISOString(),
        end_date: query.end_date.toISOString(),
        available_slots: slots.map(slot => ({
          start: slot.start.toISOString(),
          end: slot.end.toISOString()
        }))
      });
    } catch (err: any) {
      app.log.error(err);

      if (err instanceof z.ZodError) {
        return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid query parameters'));
      }

      return reply.code(500).send(ApiError('PC-AVAIL-500', 'Unexpected error'));
    }
  });

  // Create availability window (host only - auth required)
  app.post('/api/availability/windows', async (req, reply) => {
    try {
      const parsed = CreateAvailabilityWindowSchema.parse(req.body);

      const window = await availabilityService.createAvailabilityWindow({
        listingId: parsed.listing_id,
        dayOfWeek: parsed.day_of_week,
        startTime: parsed.start_time,
        endTime: parsed.end_time,
        startDate: parsed.start_date,
        endDate: parsed.end_date,
        isRecurring: parsed.is_recurring
      });

      return reply.code(201).send({
        id: window.id,
        listing_id: window.listingId,
        created_at: window.createdAt.toISOString()
      });
    } catch (err: any) {
      app.log.error(err);

      if (err instanceof z.ZodError) {
        return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid request body'));
      }

      if (err.message === 'Listing not found') {
        return reply.code(404).send(ApiError('PC-LIST-404', 'Listing not found'));
      }

      return reply.code(500).send(ApiError('PC-AVAIL-500', 'Unexpected error'));
    }
  });

  // Delete availability window
  app.delete('/api/availability/windows/:id', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      await availabilityService.deleteAvailabilityWindow(id);
      return reply.code(204).send();
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send(ApiError('PC-AVAIL-500', 'Unexpected error'));
    }
  });

  app.addHook('onClose', async () => {
    await prisma.$disconnect();
  });
}
