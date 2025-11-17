import type { PrismaClient, Booking as PrismaBooking, BookingStatus } from '@prisma/client';
import Redis from 'ioredis';
import { log } from '@prep/logger';
import { AvailabilityService } from './AvailabilityService';

export interface CreateBookingParams {
  listingId: string;
  renterId: string;
  startTime: Date;
  endTime: Date;
  hourlyRateCents: number;
  subtotalCents: number;
  serviceFeeCents: number;
  totalCents: number;
}

export interface Booking {
  id: string;
  listingId: string;
  renterId: string;
  startTime: Date;
  endTime: Date;
  status: BookingStatus;
  hourlyRateCents: number;
  subtotalCents: number;
  serviceFeeCents: number;
  totalCents: number;
  createdAt: Date;
  updatedAt: Date;
}

// Custom error types for better error handling
export class BookingConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BookingConflictError';
  }
}

export class BookingLockError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BookingLockError';
  }
}

export class BookingCreationError extends Error {
  constructor(message: string, public cause?: unknown) {
    super(message);
    this.name = 'BookingCreationError';
  }
}

/**
 * BookingService handles booking creation, validation, and persistence.
 */
export class BookingService {
  private availabilityService: AvailabilityService;

  constructor(
    private prisma: PrismaClient,
    private redis: Redis
  ) {
    this.availabilityService = new AvailabilityService(prisma, redis);
  }

  /**
   * Create a new booking with status 'requested'.
   *
   * Process:
   * 1. Validate request parameters
   * 2. Check availability atomically
   * 3. Create Redis lock for the timeslot
   * 4. Insert booking record into database
   * 5. Return booking
   *
   * On failure, automatically releases Redis lock to prevent resource leaks.
   *
   * @param params - Booking creation parameters
   * @returns Created booking
   * @throws {BookingConflictError} If listing not available
   * @throws {BookingLockError} If unable to acquire lock
   * @throws {BookingCreationError} For other creation errors
   */
  async createBooking(params: CreateBookingParams): Promise<Booking> {
    const { listingId, renterId, startTime, endTime } = params;

    // Step 1: Validate request
    this.validateBookingParams(params);

    let lockAcquired = false;
    let bookingId: string | null = null;

    try {
      // Step 2: Check availability with database lock
      const availabilityCheck = await this.availabilityService.check({
        listingId,
        start: startTime,
        end: endTime
      });

      if (!availabilityCheck.available) {
        throw new BookingConflictError('Listing not available for selected time range');
      }

      // Step 3: Create booking with Prisma transaction
      const booking = await this.prisma.$transaction(async (tx) => {
        // Create booking record
        const newBooking = await tx.booking.create({
          data: {
            listingId,
            renterId,
            startTime,
            endTime,
            status: 'requested',
            hourlyRateCents: params.hourlyRateCents,
            subtotalCents: params.subtotalCents,
            serviceFeeCents: params.serviceFeeCents,
            totalCents: params.totalCents,
            paymentStatus: 'pending'
          }
        });

        bookingId = newBooking.id;

        // Create Redis lock
        lockAcquired = await this.availabilityService.createLock(
          listingId,
          startTime,
          endTime,
          bookingId
        );

        if (!lockAcquired) {
          throw new BookingLockError('Failed to acquire booking lock');
        }

        return newBooking;
      });

      log.info('Booking created successfully', {
        bookingId: booking.id,
        listingId,
        renterId,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
      });

      return this.mapPrismaBooking(booking);

    } catch (error) {
      // Release Redis lock if acquired
      if (lockAcquired && bookingId) {
        await this.availabilityService.releaseLock(
          listingId,
          startTime,
          endTime,
          bookingId
        ).catch(lockError => {
          log.error('Failed to release lock after error', lockError as Error, {
            bookingId,
            listingId,
            startTime: startTime.toISOString(),
            endTime: endTime.toISOString(),
          });
        });
      }

      log.error('Booking creation failed', error as Error, {
        listingId,
        renterId,
        bookingId,
      });

      // Rethrow with appropriate error type
      if (error instanceof BookingConflictError || error instanceof BookingLockError) {
        throw error;
      }

      throw new BookingCreationError('Failed to create booking', error);
    }
  }

  /**
   * Validate booking parameters.
   * @throws {Error} If parameters are invalid
   */
  private validateBookingParams(params: CreateBookingParams): void {
    const { listingId, renterId, startTime, endTime } = params;

    if (!listingId || typeof listingId !== 'string') {
      throw new Error('Invalid listingId');
    }

    if (!renterId || typeof renterId !== 'string') {
      throw new Error('Invalid renterId');
    }

    if (!(startTime instanceof Date) || isNaN(startTime.getTime())) {
      throw new Error('Invalid startTime');
    }

    if (!(endTime instanceof Date) || isNaN(endTime.getTime())) {
      throw new Error('Invalid endTime');
    }

    if (startTime >= endTime) {
      throw new Error('startTime must be before endTime');
    }

    if (startTime < new Date()) {
      throw new Error('Cannot book in the past');
    }

    // Minimum booking duration: 1 hour
    const MIN_DURATION_MS = 60 * 60 * 1000;
    if (endTime.getTime() - startTime.getTime() < MIN_DURATION_MS) {
      throw new Error('Booking duration must be at least 1 hour');
    }

    // Maximum booking duration: 30 days
    const MAX_DURATION_MS = 30 * 24 * 60 * 60 * 1000;
    if (endTime.getTime() - startTime.getTime() > MAX_DURATION_MS) {
      throw new Error('Booking duration cannot exceed 30 days');
    }
  }

  /**
   * Get booking by ID.
   */
  async getBooking(bookingId: string): Promise<Booking | null> {
    const booking = await this.prisma.booking.findUnique({
      where: { id: bookingId }
    });

    if (!booking) {
      return null;
    }

    return this.mapPrismaBooking(booking);
  }

  /**
   * Update booking status.
   */
  async updateBookingStatus(bookingId: string, status: BookingStatus): Promise<Booking> {
    const booking = await this.prisma.booking.update({
      where: { id: bookingId },
      data: { status }
    });

    return this.mapPrismaBooking(booking);
  }

  /**
   * Map Prisma booking to Booking interface.
   */
  private mapPrismaBooking(booking: PrismaBooking): Booking {
    return {
      id: booking.id,
      listingId: booking.listingId,
      renterId: booking.renterId,
      startTime: booking.startTime,
      endTime: booking.endTime,
      status: booking.status,
      hourlyRateCents: booking.hourlyRateCents,
      subtotalCents: booking.subtotalCents,
      serviceFeeCents: booking.serviceFeeCents,
      totalCents: booking.totalCents,
      createdAt: booking.createdAt,
      updatedAt: booking.updatedAt,
    };
  }
}
