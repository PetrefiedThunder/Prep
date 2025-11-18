import type { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import { log } from '@prep/logger';

export interface AvailabilityCheck {
  listingId: string;
  start: Date;
  end: Date;
}

export interface AvailabilityResult {
  available: boolean;
  conflictingBookings?: string[];
}

/**
 * AvailabilityService provides atomic availability checking with database-level locking
 * to prevent race conditions during concurrent booking attempts.
 */
export class AvailabilityService {
  constructor(
    private prisma: PrismaClient,
    private redis: Redis
  ) {}

  /**
   * Check if a kitchen is available for the given time range using SELECT FOR UPDATE
   * to ensure concurrency safety.
   *
   * @param params - Listing ID and time range
   * @returns Availability result
   */
  async check(params: AvailabilityCheck): Promise<AvailabilityResult> {
    const { listingId, start, end } = params;

    // Validate time range
    if (start >= end) {
      throw new Error('Start time must be before end time');
    }

    if (start < new Date()) {
      throw new Error('Cannot book in the past');
    }

    try {
      // Use Prisma's $transaction with raw SQL for SELECT FOR UPDATE
      // This ensures atomic checking with row-level locks
      const conflictingBookings = await this.prisma.$transaction(async (tx) => {
        // Raw SQL query with FOR UPDATE to lock rows
        const conflicts = await tx.$queryRaw<Array<{ id: string }>>`
          SELECT id
          FROM bookings
          WHERE listing_id = ${listingId}::uuid
            AND status NOT IN ('canceled', 'no_show')
            AND (
              -- New booking starts during existing booking
              (start_time <= ${start} AND end_time > ${start})
              -- New booking ends during existing booking
              OR (start_time < ${end} AND end_time >= ${end})
              -- New booking completely contains existing booking
              OR (start_time >= ${start} AND end_time <= ${end})
            )
          FOR UPDATE
        `;

        return conflicts.map(c => c.id);
      });

      if (conflictingBookings.length > 0) {
        log.warn('Availability conflict detected', {
          listingId,
          start,
          end,
          conflicts: conflictingBookings.length
        });

        return {
          available: false,
          conflictingBookings
        };
      }

      // Check Redis lock as additional safeguard
      const lockKey = `booking:lock:${listingId}:${start.toISOString()}:${end.toISOString()}`;
      const existingLock = await this.redis.get(lockKey);

      if (existingLock) {
        log.warn('Redis lock exists for timeslot', { listingId, start, end });
        return {
          available: false,
          conflictingBookings: [existingLock]
        };
      }

      return { available: true };

    } catch (error) {
      log.error('Availability check failed', error);
      throw error;
    }
  }

  /**
   * Create a temporary Redis lock for a timeslot during booking creation.
   * Lock expires after 10 minutes if not confirmed.
   *
   * @param listingId - Listing identifier
   * @param start - Start time
   * @param end - End time
   * @param bookingId - Booking ID that holds the lock
   * @returns True if lock was acquired
   */
  async createLock(listingId: string, start: Date, end: Date, bookingId: string): Promise<boolean> {
    const lockKey = `booking:lock:${listingId}:${start.toISOString()}:${end.toISOString()}`;
    const lockTTL = 600; // 10 minutes in seconds

    // Use SET NX (set if not exists) for atomic lock acquisition
    const result = await this.redis.set(lockKey, bookingId, 'EX', lockTTL, 'NX');

    if (result === 'OK') {
      log.info('Created booking lock', { listingId, bookingId, ttl: lockTTL });
      return true;
    }

    log.warn('Failed to acquire booking lock', { listingId, bookingId });
    return false;
  }

  /**
   * Release a Redis lock for a timeslot.
   *
   * @param listingId - Listing identifier
   * @param start - Start time
   * @param end - End time
   * @param bookingId - Booking ID that should hold the lock
   * @returns True if lock was released
   */
  async releaseLock(listingId: string, start: Date, end: Date, bookingId: string): Promise<boolean> {
    const lockKey = `booking:lock:${listingId}:${start.toISOString()}:${end.toISOString()}`;

    // Only release if the booking_id matches (to prevent releasing someone else's lock)
    const currentLock = await this.redis.get(lockKey);

    if (currentLock === bookingId) {
      await this.redis.del(lockKey);
      log.info('Released booking lock', { listingId, bookingId });
      return true;
    }

    log.warn('Lock release failed - booking ID mismatch', {
      listingId,
      expected: bookingId,
      actual: currentLock
    });

    return false;
  }

  /**
   * Extend lock expiration for pending bookings that need more time.
   */
  async extendLock(listingId: string, start: Date, end: Date, bookingId: string, ttlSeconds: number = 600): Promise<boolean> {
    const lockKey = `booking:lock:${listingId}:${start.toISOString()}:${end.toISOString()}`;
    const currentLock = await this.redis.get(lockKey);

    if (currentLock === bookingId) {
      await this.redis.expire(lockKey, ttlSeconds);
      return true;
    }

    return false;
  }
}
