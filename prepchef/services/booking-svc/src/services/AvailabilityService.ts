import { Pool } from 'pg';
import Redis from 'ioredis';
import { log } from '@prep/logger';

export interface AvailabilityCheck {
  kitchen_id: string;
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
    private db: Pool,
    private redis: Redis
  ) {}

  /**
   * Check if a kitchen is available for the given time range using SELECT FOR UPDATE
   * to ensure concurrency safety.
   *
   * @param params - Kitchen ID and time range
   * @returns Availability result
   */
  async check(params: AvailabilityCheck): Promise<AvailabilityResult> {
    const { kitchen_id, start, end } = params;

    // Validate time range
    if (start >= end) {
      throw new Error('Start time must be before end time');
    }

    if (start < new Date()) {
      throw new Error('Cannot book in the past');
    }

    const client = await this.db.connect();

    try {
      // Start transaction for atomic check
      await client.query('BEGIN');

      // Use SELECT FOR UPDATE to lock rows and prevent race conditions
      // This query finds any overlapping bookings that are not cancelled
      const result = await client.query(
        `
        SELECT booking_id, start_time, end_time
        FROM bookings
        WHERE kitchen_id = $1
          AND status NOT IN ('cancelled', 'rejected')
          AND (
            -- New booking starts during existing booking
            (start_time <= $2 AND end_time > $2)
            -- New booking ends during existing booking
            OR (start_time < $3 AND end_time >= $3)
            -- New booking completely contains existing booking
            OR (start_time >= $2 AND end_time <= $3)
          )
        FOR UPDATE
        `,
        [kitchen_id, start.toISOString(), end.toISOString()]
      );

      await client.query('COMMIT');

      if (result.rows.length > 0) {
        log.warn('Availability conflict detected', {
          kitchen_id,
          start,
          end,
          conflicts: result.rows.length
        });

        return {
          available: false,
          conflictingBookings: result.rows.map(r => r.booking_id)
        };
      }

      // Check Redis lock as additional safeguard
      const lockKey = `booking:lock:${kitchen_id}:${start.toISOString()}:${end.toISOString()}`;
      const existingLock = await this.redis.get(lockKey);

      if (existingLock) {
        log.warn('Redis lock exists for timeslot', { kitchen_id, start, end });
        return {
          available: false,
          conflictingBookings: [existingLock]
        };
      }

      return { available: true };

    } catch (error) {
      await client.query('ROLLBACK');
      log.error('Availability check failed', error);
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Create a temporary Redis lock for a timeslot during booking creation.
   * Lock expires after 10 minutes if not confirmed.
   *
   * @param kitchen_id - Kitchen identifier
   * @param start - Start time
   * @param end - End time
   * @param booking_id - Booking ID that holds the lock
   * @returns True if lock was acquired
   */
  async createLock(kitchen_id: string, start: Date, end: Date, booking_id: string): Promise<boolean> {
    const lockKey = `booking:lock:${kitchen_id}:${start.toISOString()}:${end.toISOString()}`;
    const lockTTL = 600; // 10 minutes in seconds

    // Use SET NX (set if not exists) for atomic lock acquisition
    const result = await this.redis.set(lockKey, booking_id, 'EX', lockTTL, 'NX');

    if (result === 'OK') {
      log.info('Created booking lock', { kitchen_id, booking_id, ttl: lockTTL });
      return true;
    }

    log.warn('Failed to acquire booking lock', { kitchen_id, booking_id });
    return false;
  }

  /**
   * Release a Redis lock for a timeslot.
   *
   * @param kitchen_id - Kitchen identifier
   * @param start - Start time
   * @param end - End time
   * @param booking_id - Booking ID that should hold the lock
   * @returns True if lock was released
   */
  async releaseLock(kitchen_id: string, start: Date, end: Date, booking_id: string): Promise<boolean> {
    const lockKey = `booking:lock:${kitchen_id}:${start.toISOString()}:${end.toISOString()}`;

    // Only release if the booking_id matches (to prevent releasing someone else's lock)
    const currentLock = await this.redis.get(lockKey);

    if (currentLock === booking_id) {
      await this.redis.del(lockKey);
      log.info('Released booking lock', { kitchen_id, booking_id });
      return true;
    }

    log.warn('Lock release failed - booking ID mismatch', {
      kitchen_id,
      expected: booking_id,
      actual: currentLock
    });

    return false;
  }

  /**
   * Extend lock expiration for pending bookings that need more time.
   */
  async extendLock(kitchen_id: string, start: Date, end: Date, booking_id: string, ttlSeconds: number = 600): Promise<boolean> {
    const lockKey = `booking:lock:${kitchen_id}:${start.toISOString()}:${end.toISOString()}`;
    const currentLock = await this.redis.get(lockKey);

    if (currentLock === booking_id) {
      await this.redis.expire(lockKey, ttlSeconds);
      return true;
    }

    return false;
  }
}
