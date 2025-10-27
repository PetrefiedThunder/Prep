/**
 * Booking Hold & Release Worker (B7)
 * Runs every minute to find pending bookings older than 10 minutes,
 * releases Redis locks, and cancels the booking.
 */

import { Pool } from 'pg';
import Redis from 'ioredis';
import { log } from '@prep/logger';

export class BookingHoldWorker {
  private interval: NodeJS.Timeout | null = null;

  constructor(
    private db: Pool,
    private redis: Redis,
    private intervalMs: number = 60000 // 1 minute
  ) {}

  start() {
    log.info('Starting BookingHoldWorker');
    this.interval = setInterval(() => this.processExpiredHolds(), this.intervalMs);
  }

  stop() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
      log.info('Stopped BookingHoldWorker');
    }
  }

  async processExpiredHolds() {
    try {
      // Find pending bookings older than 10 minutes
      const result = await this.db.query(
        `
        SELECT booking_id, kitchen_id, start_time, end_time
        FROM bookings
        WHERE status = 'pending'
          AND created_at < NOW() - INTERVAL '10 minutes'
        LIMIT 100
        `
      );

      for (const row of result.rows) {
        await this.releaseExpiredHold(row);
      }

      if (result.rows.length > 0) {
        log.info(`Released ${result.rows.length} expired booking holds`);
      }
    } catch (error) {
      log.error('Error processing expired holds', error);
    }
  }

  private async releaseExpiredHold(booking: any) {
    const { booking_id, kitchen_id, start_time, end_time } = booking;

    try {
      // Release Redis lock
      const lockKey = `booking:lock:${kitchen_id}:${new Date(start_time).toISOString()}:${new Date(end_time).toISOString()}`;
      const currentLock = await this.redis.get(lockKey);

      if (currentLock === booking_id) {
        await this.redis.del(lockKey);
        log.info('Released Redis lock for expired booking', { booking_id, lockKey });
      }

      // Cancel booking
      await this.db.query(
        `UPDATE bookings SET status = 'cancelled', updated_at = NOW() WHERE booking_id = $1`,
        [booking_id]
      );

      log.info('Cancelled expired booking', { booking_id });
    } catch (error) {
      log.error('Failed to release expired hold', { booking_id, error });
    }
  }
}
