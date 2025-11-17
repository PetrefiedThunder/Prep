import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';
import { ListingService } from '../services/ListingService';
import { getPrismaClient } from '@prep/database';

const ListingsQuerySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
  is_active: z.coerce.boolean().optional(),
  is_featured: z.coerce.boolean().optional(),
  min_hourly_rate: z.coerce.number().int().nonnegative().optional(),
  max_hourly_rate: z.coerce.number().int().positive().optional(),
  kitchen_types: z.string().optional().transform(val => val ? val.split(',') : undefined)
});

const CreateListingSchema = z.object({
  venue_id: z.string().uuid(),
  title: z.string().min(1).max(255),
  description: z.string().optional(),
  kitchen_type: z.array(z.string()).min(1),
  equipment: z.any().optional(),
  hourly_rate_cents: z.number().int().positive(),
  daily_rate_cents: z.number().int().positive().optional(),
  weekly_rate_cents: z.number().int().positive().optional(),
  monthly_rate_cents: z.number().int().positive().optional(),
  minimum_hours: z.number().int().positive().default(2),
  cleaning_fee_cents: z.number().int().nonnegative().default(0),
  security_deposit_cents: z.number().int().nonnegative().default(0),
  features: z.array(z.string()).default([]),
  restrictions: z.array(z.string()).default([]),
  photos: z.array(z.string().url()).default([])
});

const UpdateListingSchema = CreateListingSchema.partial().omit({ venue_id: true });

export default async function (app: FastifyInstance) {
  const prisma = getPrismaClient();
  const listingService = new ListingService(prisma);

  // List all kitchen listings
  app.get('/api/listings', async (req, reply) => {
    try {
      const query = ListingsQuerySchema.parse(req.query);

      const result = await listingService.listListings(
        {
          isActive: query.is_active,
          isFeatured: query.is_featured,
          minHourlyRate: query.min_hourly_rate,
          maxHourlyRate: query.max_hourly_rate,
          kitchenTypes: query.kitchen_types
        },
        {
          page: query.page,
          limit: query.limit
        }
      );

      return reply.code(200).send({
        listings: result.listings.map(listing => ({
          id: listing.id,
          venue_id: listing.venueId,
          title: listing.title,
          description: listing.description,
          kitchen_type: listing.kitchenType,
          equipment: listing.equipment,
          hourly_rate_cents: listing.hourlyRateCents,
          minimum_hours: listing.minimumHours,
          is_active: listing.isActive,
          is_featured: listing.isFeatured,
          average_rating: listing.averageRating,
          total_reviews: listing.totalReviews,
          photos: listing.photos,
          features: listing.features,
          created_at: listing.createdAt.toISOString(),
          updated_at: listing.updatedAt.toISOString()
        })),
        pagination: {
          total: result.total,
          page: result.page,
          limit: query.limit,
          total_pages: result.totalPages
        }
      });
    } catch (err: any) {
      app.log.error(err);

      if (err instanceof z.ZodError) {
        return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid query parameters'));
      }

      return reply.code(500).send(ApiError('PC-LIST-500', 'Unexpected error'));
    }
  });

  // Get single listing by ID
  app.get('/api/listings/:id', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      const listing = await listingService.getListing(id);

      if (!listing) {
        return reply.code(404).send(ApiError('PC-LIST-404', 'Listing not found'));
      }

      return reply.code(200).send({
        id: listing.id,
        venue_id: listing.venueId,
        title: listing.title,
        description: listing.description,
        kitchen_type: listing.kitchenType,
        equipment: listing.equipment,
        hourly_rate_cents: listing.hourlyRateCents,
        minimum_hours: listing.minimumHours,
        is_active: listing.isActive,
        is_featured: listing.isFeatured,
        average_rating: listing.averageRating,
        total_reviews: listing.totalReviews,
        photos: listing.photos,
        features: listing.features,
        created_at: listing.createdAt.toISOString(),
        updated_at: listing.updatedAt.toISOString()
      });
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send(ApiError('PC-LIST-500', 'Unexpected error'));
    }
  });

  // Create new listing (host only - auth required)
  app.post('/api/listings', async (req, reply) => {
    try {
      const parsed = CreateListingSchema.parse(req.body);

      const listing = await listingService.createListing({
        venueId: parsed.venue_id,
        title: parsed.title,
        description: parsed.description,
        kitchenType: parsed.kitchen_type,
        equipment: parsed.equipment,
        hourlyRateCents: parsed.hourly_rate_cents,
        dailyRateCents: parsed.daily_rate_cents,
        weeklyRateCents: parsed.weekly_rate_cents,
        monthlyRateCents: parsed.monthly_rate_cents,
        minimumHours: parsed.minimum_hours,
        cleaningFeeCents: parsed.cleaning_fee_cents,
        securityDepositCents: parsed.security_deposit_cents,
        features: parsed.features,
        restrictions: parsed.restrictions,
        photos: parsed.photos
      });

      return reply.code(201).send({
        id: listing.id,
        venue_id: listing.venueId,
        title: listing.title,
        created_at: listing.createdAt.toISOString()
      });
    } catch (err: any) {
      app.log.error(err);

      if (err instanceof z.ZodError) {
        return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid request body'));
      }

      if (err.message === 'Venue not found') {
        return reply.code(404).send(ApiError('PC-VENUE-404', 'Venue not found'));
      }

      return reply.code(500).send(ApiError('PC-LIST-500', 'Unexpected error'));
    }
  });

  // Update listing (host only - auth required)
  app.patch('/api/listings/:id', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      const parsed = UpdateListingSchema.parse(req.body);

      const updates: any = {};
      if (parsed.title !== undefined) updates.title = parsed.title;
      if (parsed.description !== undefined) updates.description = parsed.description;
      if (parsed.kitchen_type !== undefined) updates.kitchenType = parsed.kitchen_type;
      if (parsed.equipment !== undefined) updates.equipment = parsed.equipment;
      if (parsed.hourly_rate_cents !== undefined) updates.hourlyRateCents = parsed.hourly_rate_cents;
      if (parsed.daily_rate_cents !== undefined) updates.dailyRateCents = parsed.daily_rate_cents;
      if (parsed.weekly_rate_cents !== undefined) updates.weeklyRateCents = parsed.weekly_rate_cents;
      if (parsed.monthly_rate_cents !== undefined) updates.monthlyRateCents = parsed.monthly_rate_cents;
      if (parsed.minimum_hours !== undefined) updates.minimumHours = parsed.minimum_hours;
      if (parsed.cleaning_fee_cents !== undefined) updates.cleaningFeeCents = parsed.cleaning_fee_cents;
      if (parsed.security_deposit_cents !== undefined) updates.securityDepositCents = parsed.security_deposit_cents;
      if (parsed.features !== undefined) updates.features = parsed.features;
      if (parsed.restrictions !== undefined) updates.restrictions = parsed.restrictions;
      if (parsed.photos !== undefined) updates.photos = parsed.photos;

      const listing = await listingService.updateListing(id, updates);

      return reply.code(200).send({
        id: listing.id,
        updated_at: listing.updatedAt.toISOString()
      });
    } catch (err: any) {
      app.log.error(err);

      if (err instanceof z.ZodError) {
        return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid request body'));
      }

      return reply.code(500).send(ApiError('PC-LIST-500', 'Unexpected error'));
    }
  });

  // Delete listing (soft delete)
  app.delete('/api/listings/:id', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      await listingService.deleteListing(id);
      return reply.code(204).send();
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send(ApiError('PC-LIST-500', 'Unexpected error'));
    }
  });

  app.addHook('onClose', async () => {
    await prisma.$disconnect();
  });
}
