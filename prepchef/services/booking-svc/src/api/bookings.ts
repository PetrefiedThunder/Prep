import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';
import { getPrismaClient } from '@prep/database';
import Redis from 'ioredis';

const CreateBookingSchema = z.object({
  listing_id: z.string().uuid(),
  renter_id: z.string().uuid(),
  start_time: z.string().datetime(),
  end_time: z.string().datetime()
});

const ConfirmBookingSchema = z.object({
  payment_method: z.string().optional()
});

export default async function (app: FastifyInstance) {
  const prisma = getPrismaClient();

  const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379/0');
  await redis.connect().catch(() => {});

  app.post('/bookings', async (req, reply) => {
    const parsed = CreateBookingSchema.safeParse(req.body);

    if (!parsed.success) {
      return reply.code(400).send({
        error: 'Invalid request body',
        details: parsed.error.flatten().fieldErrors
      });
    }

    const { listing_id, renter_id, start_time, end_time } = parsed.data;
    const startDate = new Date(start_time);
    const endDate = new Date(end_time);

    try {
      // Check if listing exists
      const listing = await prisma.kitchenListing.findUnique({
        where: { id: listing_id },
        include: { venue: true }
      });

      if (!listing || !listing.isActive) {
        return reply.code(404).send({ error: 'Kitchen listing not found or inactive' });
      }

      // Check for booking conflicts (simplified - real implementation would use Redis locks)
      const conflictingBookings = await prisma.booking.findMany({
        where: {
          listingId: listing_id,
          status: { in: ['requested', 'payment_authorized', 'confirmed', 'active'] },
          OR: [
            {
              AND: [
                { startTime: { lte: startDate } },
                { endTime: { gt: startDate } }
              ]
            },
            {
              AND: [
                { startTime: { lt: endDate } },
                { endTime: { gte: endDate } }
              ]
            },
            {
              AND: [
                { startTime: { gte: startDate } },
                { endTime: { lte: endDate } }
              ]
            }
          ]
        }
      });

      if (conflictingBookings.length > 0) {
        return reply.code(409).send({ error: 'Kitchen not available for selected time' });
      }

      // Calculate pricing
      const hours = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60);
      const subtotalCents = Math.round(hours * listing.hourlyRateCents);
      const serviceFeeCents = Math.round(subtotalCents * 0.20); // 20% platform fee
      const taxCents = Math.round((subtotalCents + serviceFeeCents) * 0.085); // 8.5% tax
      const totalCents = subtotalCents + listing.cleaningFeeCents + serviceFeeCents + taxCents;

      // Create booking
      const booking = await prisma.booking.create({
        data: {
          listingId: listing_id,
          renterId: renter_id,
          startTime: startDate,
          endTime: endDate,
          status: 'requested',
          hourlyRateCents: listing.hourlyRateCents,
          subtotalCents,
          cleaningFeeCents: listing.cleaningFeeCents,
          serviceFeeCents,
          taxCents,
          totalCents,
          securityDepositCents: listing.securityDepositCents,
          paymentStatus: 'pending'
        }
      });

      return reply.code(201).send({
        id: booking.id,
        listing_id: booking.listingId,
        status: booking.status,
        start_time: booking.startTime.toISOString(),
        end_time: booking.endTime.toISOString(),
        total_cents: booking.totalCents,
        breakdown: {
          subtotal_cents: booking.subtotalCents,
          cleaning_fee_cents: booking.cleaningFeeCents,
          service_fee_cents: booking.serviceFeeCents,
          tax_cents: booking.taxCents
        }
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

      if (booking.status !== 'requested') {
        return reply.code(400).send({ error: 'Booking cannot be confirmed in current state' });
      }

      // This will be called from frontend to initiate payment
      // We'll return the booking details and total for Stripe payment
      return reply.code(200).send({
        id: booking.id,
        total_cents: booking.totalCents,
        // client_secret will be added by payments-svc
        ready_for_payment: true
      });

    } catch (err) {
      app.log.error(err);
      return reply.code(500).send({ error: 'Failed to confirm booking' });
    }
  });

  app.addHook('onClose', async () => {
    await prisma.$disconnect();
    await redis.quit();
  });
}
