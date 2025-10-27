import { Pool } from 'pg';
import Redis from 'ioredis';
import { randomUUID } from 'crypto';
import { log } from '@prep/logger';
import { AvailabilityService } from './AvailabilityService';

export interface CreateBookingParams {
  kitchen_id: string;
  user_id: string;
  start_time: Date;
  end_time: Date;
  listing_id?: string;
}

export interface Booking {
  booking_id: string;
  kitchen_id: string;
  user_id: string;
  start_time: Date;
  end_time: Date;
  status: 'pending' | 'confirmed' | 'cancelled' | 'rejected';
  created_at: Date;
  updated_at: Date;
}

/**
 * BookingService handles booking creation, validation, and persistence.
 */
export class BookingService {
  private availabilityService: AvailabilityService;

  constructor(
    private db: Pool,
    private redis: Redis
  ) {
    this.availabilityService = new AvailabilityService(db, redis);
  }

  /**
   * Create a new booking with status 'pending'.
   *
   * Process:
   * 1. Validate request parameters
   * 2. Check availability atomically
   * 3. Create Redis lock for the timeslot
   * 4. Insert booking record into database
   * 5. Return booking ID
   *
   * @param params - Booking creation parameters
   * @returns Created booking
   */
  async createBooking(params: CreateBookingParams): Promise<Booking> {
    const { kitchen_id, user_id, start_time, end_time } = params;

    // Step 1: Validate request
    this.validateBookingParams(params);

    const client = await this.db.connect();

    try {
      // Step 2: Check availability with database lock
      const availabilityCheck = await this.availabilityService.check({
        kitchen_id,
        start: start_time,
        end: end_time
      });

      if (!availabilityCheck.available) {
        throw new Error('Kitchen not available for selected time range');
      }

      // Step 3: Create Redis lock
      const booking_id = randomUUID();
      const lockAcquired = await this.availabilityService.createLock(
        kitchen_id,
        start_time,
        end_time,
        booking_id
      );

      if (!lockAcquired) {
        throw new Error('Failed to acquire booking lock');
      }

      // Step 4: Insert booking record
      await client.query('BEGIN');

      const insertResult = await client.query(
        `
        INSERT INTO bookings (
          booking_id,
          kitchen_id,
          user_id,
          start_time,
          end_time,
          status,
          created_at,
          updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
        RETURNING *
        `,
        [booking_id, kitchen_id, user_id, start_time.toISOString(), end_time.toISOString(), 'pending']
      );

      await client.query('COMMIT');

      const booking = this.mapRowToBooking(insertResult.rows[0]);

      log.info('Booking created', {
        booking_id,
        kitchen_id,
        user_id,
        start_time,
        end_time
      });

      return booking;

    } catch (error) {
      await client.query('ROLLBACK');
      log.error('Booking creation failed', error);
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Validate booking parameters.
   */
  private validateBookingParams(params: CreateBookingParams): void {
    const { kitchen_id, user_id, start_time, end_time } = params;

    if (!kitchen_id || typeof kitchen_id !== 'string') {
      throw new Error('Invalid kitchen_id');
    }

    if (!user_id || typeof user_id !== 'string') {
      throw new Error('Invalid user_id');
    }

    if (!(start_time instanceof Date) || isNaN(start_time.getTime())) {
      throw new Error('Invalid start_time');
    }

    if (!(end_time instanceof Date) || isNaN(end_time.getTime())) {
      throw new Error('Invalid end_time');
    }

    if (start_time >= end_time) {
      throw new Error('start_time must be before end_time');
    }

    if (start_time < new Date()) {
      throw new Error('Cannot book in the past');
    }

    // Minimum booking duration: 1 hour
    const minDuration = 60 * 60 * 1000; // 1 hour in milliseconds
    if (end_time.getTime() - start_time.getTime() < minDuration) {
      throw new Error('Booking duration must be at least 1 hour');
    }

    // Maximum booking duration: 30 days
    const maxDuration = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds
    if (end_time.getTime() - start_time.getTime() > maxDuration) {
      throw new Error('Booking duration cannot exceed 30 days');
    }
  }

  /**
   * Get booking by ID.
   */
  async getBooking(booking_id: string): Promise<Booking | null> {
    const result = await this.db.query(
      'SELECT * FROM bookings WHERE booking_id = $1',
      [booking_id]
    );

    if (result.rows.length === 0) {
      return null;
    }

    return this.mapRowToBooking(result.rows[0]);
  }

  /**
   * Update booking status.
   */
  async updateBookingStatus(booking_id: string, status: Booking['status']): Promise<Booking> {
    const result = await this.db.query(
      `
      UPDATE bookings
      SET status = $1, updated_at = NOW()
      WHERE booking_id = $2
      RETURNING *
      `,
      [status, booking_id]
    );

    if (result.rows.length === 0) {
      throw new Error('Booking not found');
    }

    return this.mapRowToBooking(result.rows[0]);
  }

  /**
   * Map database row to Booking object.
   */
  private mapRowToBooking(row: any): Booking {
    return {
      booking_id: row.booking_id,
      kitchen_id: row.kitchen_id,
      user_id: row.user_id,
      start_time: new Date(row.start_time),
      end_time: new Date(row.end_time),
      status: row.status,
      created_at: new Date(row.created_at),
      updated_at: new Date(row.updated_at)
    };
  }
}
