import type { PrismaClient, KitchenListing as PrismaListing } from '@prisma/client';
import { log } from '@prep/logger';

export interface ListingFilters {
  isActive?: boolean;
  isFeatured?: boolean;
  minHourlyRate?: number;
  maxHourlyRate?: number;
  kitchenTypes?: string[];
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface ListingResponse {
  id: string;
  venueId: string;
  title: string;
  description: string | null;
  kitchenType: string[];
  equipment: any;
  hourlyRateCents: number;
  minimumHours: number;
  isActive: boolean;
  isFeatured: boolean;
  averageRating: number | null;
  totalReviews: number;
  photos: string[];
  features: string[];
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateListingParams {
  venueId: string;
  title: string;
  description?: string;
  kitchenType: string[];
  equipment?: any;
  hourlyRateCents: number;
  dailyRateCents?: number;
  weeklyRateCents?: number;
  monthlyRateCents?: number;
  minimumHours?: number;
  cleaningFeeCents?: number;
  securityDepositCents?: number;
  features?: string[];
  restrictions?: string[];
  photos?: string[];
}

/**
 * ListingService handles kitchen listing CRUD operations
 */
export class ListingService {
  constructor(private prisma: PrismaClient) {}

  /**
   * List all kitchen listings with filtering and pagination
   */
  async listListings(filters: ListingFilters = {}, pagination: PaginationParams = { page: 1, limit: 20 }): Promise<{ listings: ListingResponse[]; total: number; page: number; totalPages: number }> {
    const { page, limit } = pagination;
    const skip = (page - 1) * limit;

    const where: any = {};

    if (filters.isActive !== undefined) {
      where.isActive = filters.isActive;
    }

    if (filters.isFeatured !== undefined) {
      where.isFeatured = filters.isFeatured;
    }

    if (filters.minHourlyRate !== undefined || filters.maxHourlyRate !== undefined) {
      where.hourlyRateCents = {};
      if (filters.minHourlyRate !== undefined) {
        where.hourlyRateCents.gte = filters.minHourlyRate;
      }
      if (filters.maxHourlyRate !== undefined) {
        where.hourlyRateCents.lte = filters.maxHourlyRate;
      }
    }

    if (filters.kitchenTypes && filters.kitchenTypes.length > 0) {
      where.kitchenType = {
        hasSome: filters.kitchenTypes
      };
    }

    const [listings, total] = await Promise.all([
      this.prisma.kitchenListing.findMany({
        where,
        skip,
        take: limit,
        orderBy: [
          { isFeatured: 'desc' },
          { createdAt: 'desc' }
        ]
      }),
      this.prisma.kitchenListing.count({ where })
    ]);

    return {
      listings: listings.map(l => this.mapPrismaListing(l)),
      total,
      page,
      totalPages: Math.ceil(total / limit)
    };
  }

  /**
   * Get a single listing by ID
   */
  async getListing(id: string): Promise<ListingResponse | null> {
    const listing = await this.prisma.kitchenListing.findUnique({
      where: { id },
      include: {
        venue: {
          include: {
            business: true
          }
        }
      }
    });

    if (!listing) {
      return null;
    }

    return this.mapPrismaListing(listing);
  }

  /**
   * Create a new kitchen listing
   */
  async createListing(params: CreateListingParams): Promise<ListingResponse> {
    // Verify venue exists
    const venue = await this.prisma.venue.findUnique({
      where: { id: params.venueId }
    });

    if (!venue) {
      throw new Error('Venue not found');
    }

    const listing = await this.prisma.kitchenListing.create({
      data: {
        venueId: params.venueId,
        title: params.title,
        description: params.description,
        kitchenType: params.kitchenType,
        equipment: params.equipment || [],
        hourlyRateCents: params.hourlyRateCents,
        dailyRateCents: params.dailyRateCents,
        weeklyRateCents: params.weeklyRateCents,
        monthlyRateCents: params.monthlyRateCents,
        minimumHours: params.minimumHours || 2,
        cleaningFeeCents: params.cleaningFeeCents || 0,
        securityDepositCents: params.securityDepositCents || 0,
        features: params.features || [],
        restrictions: params.restrictions || [],
        photos: params.photos || [],
        isActive: true,
        isFeatured: false
      }
    });

    log.info('Kitchen listing created', {
      listingId: listing.id,
      venueId: params.venueId,
      title: params.title
    });

    return this.mapPrismaListing(listing);
  }

  /**
   * Update a listing
   */
  async updateListing(id: string, updates: Partial<CreateListingParams>): Promise<ListingResponse> {
    const listing = await this.prisma.kitchenListing.update({
      where: { id },
      data: {
        ...updates,
        updatedAt: new Date()
      }
    });

    log.info('Kitchen listing updated', { listingId: id });

    return this.mapPrismaListing(listing);
  }

  /**
   * Delete (soft delete) a listing
   */
  async deleteListing(id: string): Promise<void> {
    await this.prisma.kitchenListing.update({
      where: { id },
      data: {
        isActive: false,
        deletedAt: new Date()
      }
    });

    log.info('Kitchen listing deleted', { listingId: id });
  }

  /**
   * Map Prisma listing to response format
   */
  private mapPrismaListing(listing: PrismaListing): ListingResponse {
    return {
      id: listing.id,
      venueId: listing.venueId,
      title: listing.title,
      description: listing.description,
      kitchenType: listing.kitchenType,
      equipment: listing.equipment,
      hourlyRateCents: listing.hourlyRateCents,
      minimumHours: listing.minimumHours,
      isActive: listing.isActive,
      isFeatured: listing.isFeatured,
      averageRating: listing.averageRating ? Number(listing.averageRating) : null,
      totalReviews: listing.totalReviews,
      photos: listing.photos,
      features: listing.features,
      createdAt: listing.createdAt,
      updatedAt: listing.updatedAt
    };
  }
}
