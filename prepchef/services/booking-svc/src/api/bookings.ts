import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';
import { BookingService } from '../services/BookingService';
import { getPrismaClient } from '@prep/database';
import { log } from '@prep/logger';
import Redis from 'ioredis';
import { env } from '@prep/config';

const CreateBookingSchema = z.object({
  listing_id: z.string().uuid(),
  renter_id: z.string().uuid(),
  start_time: z.string().datetime(),
  end_time: z.string().datetime(),
  hourly_rate_cents: z.number().int().positive(),
  subtotal_cents: z.number().int().nonnegative(),
  service_fee_cents: z.number().int().nonnegative(),
  total_cents: z.number().int().positive()
});

const ConfirmBookingSchema = z.object({
  payment_method: z.string().optional()
});

export default async function (app: FastifyInstance) {
  const prisma = getPrismaClient();

  const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379/0', {
    lazyConnect: true,
    maxRetriesPerRequest: 1,
    enableReadyCheck: false
  });

  redis.on('error', err => {
    log.warn('Redis connection error (continuing without cache)', { error: err.message });
  });

  await redis.connect().catch(() => {
    log.warn('Redis unavailable, proceeding without distributed locks');
  });

  const bookingService = new BookingService(prisma, redis);

  app.post('/api/bookings', async (req, reply) => {
    const parsed = CreateBookingSchema.safeParse(req.body);

    if (!parsed.success) {
      return reply.code(400).send({
        error: 'Invalid request body',
        details: parsed.error.flatten().fieldErrors
      });
    }

    const { listing_id, renter_id, start_time, end_time, hourly_rate_cents, subtotal_cents, service_fee_cents, total_cents } = parsed.data;

    try {
      const booking = await bookingService.createBooking({
        listingId: listing_id,
        renterId: renter_id,
        startTime: new Date(start_time),
        endTime: new Date(end_time),
        hourlyRateCents: hourly_rate_cents,
        subtotalCents: subtotal_cents,
        serviceFeeCents: service_fee_cents,
        totalCents: total_cents
      });

      return reply.code(201).send({
        id: booking.id,
        listing_id: booking.listingId,
        renter_id: booking.renterId,
        start_time: booking.startTime.toISOString(),
        end_time: booking.endTime.toISOString(),
        status: booking.status,
        hourly_rate_cents: booking.hourlyRateCents,
        subtotal_cents: booking.subtotalCents,
        service_fee_cents: booking.serviceFeeCents,
        total_cents: booking.totalCents,
        created_at: booking.createdAt.toISOString(),
        updated_at: booking.updatedAt.toISOString()
      });

    } catch (err: any) {
      app.log.error(err);
      return reply.code(500).send({ error: 'Failed to create booking' });
    }
  });

  app.get('/bookings/:id', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      const booking = await prisma.booking.findUnique({
        where: { id },
        include: {
          listing: {
            include: {
              venue: true
            }
          },
          renter: {
            select: {
              id: true,
              email: true,
              fullName: true
            }
          }
        }
      });

      if (!booking) {
        return reply.code(404).send({ error: 'Booking not found' });
      }

      return reply.code(200).send(booking);
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send({ error: 'Failed to retrieve booking' });
    }
  });

  app.post('/bookings/:id/confirm', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      const booking = await prisma.booking.findUnique({
        where: { id }
      });

      if (!booking) {
        return reply.code(404).send({ error: 'Booking not found' });
      }

      return reply.code(200).send({
        id: booking.id,
        listing_id: booking.listingId,
        renter_id: booking.renterId,
        start_time: booking.startTime.toISOString(),
        end_time: booking.endTime.toISOString(),
        status: booking.status,
        hourly_rate_cents: booking.hourlyRateCents,
        subtotal_cents: booking.subtotalCents,
        service_fee_cents: booking.serviceFeeCents,
        total_cents: booking.totalCents,
        created_at: booking.createdAt.toISOString(),
        updated_at: booking.updatedAt.toISOString()
      });
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send({ error: 'Failed to confirm booking' });
    }
  });

  app.addHook('onClose', async () => {
    await redis.quit();
    await prisma.$disconnect();
  });
}
