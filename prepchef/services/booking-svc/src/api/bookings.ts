import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';
import { BookingService } from '../services/BookingService';
import { Pool } from 'pg';
import Redis from 'ioredis';

const CreateBookingSchema = z.object({
  kitchen_id: z.string().uuid(),
  user_id: z.string().uuid(),
  start_time: z.string().datetime(),
  end_time: z.string().datetime()
});

export default async function (app: FastifyInstance) {
  const db = new Pool({
    connectionString: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/prepchef'
  });

  const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379/0');
  await redis.connect().catch(() => {});

  const bookingService = new BookingService(db, redis);

  app.post('/api/bookings', async (req, reply) => {
    const parsed = CreateBookingSchema.safeParse(req.body);

    if (!parsed.success) {
      return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid request body'));
    }

    const { kitchen_id, user_id, start_time, end_time } = parsed.data;

    try {
      const booking = await bookingService.createBooking({
        kitchen_id,
        user_id,
        start_time: new Date(start_time),
        end_time: new Date(end_time)
      });

      return reply.code(201).send({
        booking_id: booking.booking_id,
        status: booking.status,
        kitchen_id: booking.kitchen_id,
        start_time: booking.start_time.toISOString(),
        end_time: booking.end_time.toISOString()
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

      return reply.code(200).send(booking);
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send(ApiError('PC-BOOK-500', 'Unexpected error'));
    }
  });

  app.addHook('onClose', async () => {
    await db.end();
    await redis.quit();
  });
}
