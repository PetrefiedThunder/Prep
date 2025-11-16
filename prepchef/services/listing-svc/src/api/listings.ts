import { FastifyInstance } from 'fastify';
import { getPrismaClient } from '@prep/database';
import { z } from 'zod';

const SearchListingsSchema = z.object({
  location: z.string().optional(),
  date: z.string().datetime().optional(),
  min_price: z.coerce.number().optional(),
  max_price: z.coerce.number().optional(),
  equipment: z.array(z.string()).optional(),
  limit: z.coerce.number().default(20),
  offset: z.coerce.number().default(0)
});

export default async function (app: FastifyInstance) {
  const prisma = getPrismaClient();

  // Search kitchen listings
  app.get('/listings', async (req, reply) => {
    const parsed = SearchListingsSchema.safeParse(req.query);

    if (!parsed.success) {
      return reply.code(400).send({
        error: 'Invalid query parameters',
        details: parsed.error.flatten().fieldErrors
      });
    }

    const { min_price, max_price, limit, offset } = parsed.data;

    try {
      const where: any = {
        isActive: true,
        deletedAt: null
      };

      // Price filtering
      if (min_price || max_price) {
        where.hourlyRateCents = {};
        if (min_price) where.hourlyRateCents.gte = min_price * 100;
        if (max_price) where.hourlyRateCents.lte = max_price * 100;
      }

      const listings = await prisma.kitchenListing.findMany({
        where,
        include: {
          venue: {
            include: {
              business: {
                select: {
                  id: true,
                  name: true
                }
              }
            }
          }
        },
        take: limit,
        skip: offset,
        orderBy: {
          createdAt: 'desc'
        }
      });

      return reply.send({
        listings: listings.map(listing => ({
          id: listing.id,
          title: listing.title,
          description: listing.description,
          hourly_rate_cents: listing.hourlyRateCents,
          daily_rate_cents: listing.dailyRateCents,
          cleaning_fee_cents: listing.cleaningFeeCents,
          photos: listing.photos,
          equipment: listing.equipment,
          features: listing.features,
          venue: {
            id: listing.venue.id,
            name: listing.venue.name,
            address: listing.venue.address,
            business_name: listing.venue.business.name
          },
          average_rating: listing.averageRating,
          total_reviews: listing.totalReviews
        })),
        total: listings.length,
        limit,
        offset
      });

    } catch (error: any) {
      app.log.error('[listing-svc] Search failed', { error: error.message });
      return reply.code(500).send({ error: 'Failed to search listings' });
    }
  });

  // Get listing by ID
  app.get('/listings/:id', async (req, reply) => {
    const { id } = req.params as { id: string };

    try {
      const listing = await prisma.kitchenListing.findUnique({
        where: { id },
        include: {
          venue: {
            include: {
              business: {
                select: {
                  id: true,
                  name: true,
                  verified: true
                }
              }
            }
          },
          availabilityWindows: true,
          reviews: {
            where: { deletedAt: null },
            orderBy: { createdAt: 'desc' },
            take: 10,
            include: {
              reviewer: {
                select: {
                  id: true,
                  fullName: true
                }
              }
            }
          }
        }
      });

      if (!listing || listing.deletedAt || !listing.isActive) {
        return reply.code(404).send({ error: 'Listing not found' });
      }

      return reply.send({
        id: listing.id,
        title: listing.title,
        description: listing.description,
        kitchen_type: listing.kitchenType,
        equipment: listing.equipment,
        certifications: listing.certifications,
        photos: listing.photos,
        video_url: listing.videoUrl,
        hourly_rate_cents: listing.hourlyRateCents,
        daily_rate_cents: listing.dailyRateCents,
        weekly_rate_cents: listing.weeklyRateCents,
        monthly_rate_cents: listing.monthlyRateCents,
        minimum_hours: listing.minimumHours,
        cleaning_fee_cents: listing.cleaningFeeCents,
        security_deposit_cents: listing.securityDepositCents,
        advance_notice_hours: listing.advanceNoticeHours,
        max_booking_hours: listing.maxBookingHours,
        cancellation_policy: listing.cancellationPolicy,
        features: listing.features,
        restrictions: listing.restrictions,
        accessibility_features: listing.accessibilityFeatures,
        is_featured: listing.isFeatured,
        average_rating: listing.averageRating,
        total_reviews: listing.totalReviews,
        venue: {
          id: listing.venue.id,
          name: listing.venue.name,
          address: listing.venue.address,
          timezone: listing.venue.timezone,
          capacity: listing.venue.capacity,
          square_footage: listing.venue.squareFootage,
          business: {
            id: listing.venue.business.id,
            name: listing.venue.business.name,
            verified: listing.venue.business.verified
          }
        },
        availability_windows: listing.availabilityWindows.map(window => ({
          id: window.id,
          day_of_week: window.dayOfWeek,
          start_time: window.startTime,
          end_time: window.endTime,
          start_date: window.startDate,
          end_date: window.endDate,
          is_recurring: window.isRecurring
        })),
        reviews: listing.reviews.map(review => ({
          id: review.id,
          overall_rating: review.overallRating,
          cleanliness_rating: review.cleanlinessRating,
          equipment_rating: review.equipmentRating,
          location_rating: review.locationRating,
          value_rating: review.valueRating,
          title: review.title,
          comment: review.comment,
          photos: review.photos,
          reviewer: {
            id: review.reviewer.id,
            name: review.reviewer.fullName
          },
          created_at: review.createdAt
        }))
      });

    } catch (error: any) {
      app.log.error('[listing-svc] Get listing failed', { error: error.message, id });
      return reply.code(500).send({ error: 'Failed to retrieve listing' });
    }
  });

  app.addHook('onClose', async () => {
    await prisma.$disconnect();
  });
}
