import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';
import { BookingService } from '../services/BookingService';
import { getPrismaClient } from '@prep/database';
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

export default async function (app: FastifyInstance) {
  const prisma = getPrismaClient();

  const redis = new Redis(env.REDIS_URL || 'redis://localhost:6379/0');
  await redis.connect().catch(() => {});

  const bookingService = new BookingService(prisma, redis);

  app.post('/api/bookings', async (req, reply) => {
    const parsed = CreateBookingSchema.safeParse(req.body);

    if (!parsed.success) {
      return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid request body'));
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

      if (err.message.includes('not available')) {
        return reply.code(409).send(ApiError('PC-AVAIL-409', err.message));
      }

      if (err.message.includes('Invalid')) {
        return reply.code(400).send(ApiError('PC-REQ-400', err.message));
      }

      return reply.code(500).send(ApiError('PC-BOOK-500', 'Unexpected error'));
    }
  });

  app.get('/api/bookings/:id', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      const booking = await bookingService.getBooking(id);

      if (!booking) {
        return reply.code(404).send(ApiError('PC-BOOK-404', 'Booking not found'));
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
      return reply.code(500).send(ApiError('PC-BOOK-500', 'Unexpected error'));
    }
  });

  app.addHook('onClose', async () => {
    await redis.quit();
    await prisma.$disconnect();
  });
}
