/**
 * Host Payout Job (B9)
 * Aggregates confirmed bookings into weekly payouts with proper transaction handling
 */

import { Pool, PoolClient } from 'pg';
import { log } from '@prep/logger';
import { randomUUID } from 'crypto';

interface BookingPayoutRow {
  booking_id: string;
  kitchen_id: string;
  user_id: string;
  amount_cents: number;
  platform_fee_cents: number;
  host_payout_cents: number;
  created_at: Date;
  host_id: string;
  host_email: string;
  host_name: string;
  stripe_account_id: string | null;
}

interface HostPayoutData {
  host_id: string;
  host_email: string;
  host_name: string;
  stripe_account_id: string | null;
  bookings: Array<{
    booking_id: string;
    amount_cents: number;
    host_payout_cents: number;
    platform_fee_cents: number;
  }>;
  total_host_payout_cents: number;
  total_platform_fee_cents: number;
}

interface PayoutRecord {
  payout_id: string;
  host_id: string;
  host_email: string;
  host_name: string;
  booking_count: number;
  total_amount_cents: number;
  stripe_account_id: string | null;
}

interface WeeklyPayoutReport {
  status: 'success' | 'no_payouts';
  payouts: PayoutRecord[];
  report_key?: string;
}

export class PayoutService {
  constructor(private db: Pool) {}

  async generateWeeklyPayouts(): Promise<WeeklyPayoutReport> {
    let client: PoolClient | null = null;

    try {
      client = await this.db.connect();
      await client.query('BEGIN');

      // Find all confirmed bookings from last 7 days that don't have a payout
      // Use a 2-day settlement period to ensure payment has cleared
      const result = await client.query<BookingPayoutRow>(
        `SELECT
          b.booking_id,
          b.kitchen_id,
          b.user_id,
          b.amount_cents,
          COALESCE(b.platform_fee_cents, 0) as platform_fee_cents,
          COALESCE(b.host_payout_cents, b.amount_cents - COALESCE(b.platform_fee_cents, 0)) as host_payout_cents,
          b.created_at,
          k.host_id,
          k.host_email,
          k.host_name,
          k.stripe_account_id
        FROM bookings b
        JOIN kitchens k ON b.kitchen_id = k.kitchen_id
        WHERE b.status = 'confirmed'
          AND b.created_at >= NOW() - INTERVAL '7 days'
          AND b.created_at < NOW() - INTERVAL '2 days'
          AND NOT EXISTS (
            SELECT 1 FROM payout_bookings pb
            WHERE pb.booking_id = b.booking_id
          )
          AND b.amount_cents IS NOT NULL
          AND b.amount_cents > 0
        ORDER BY k.host_id, b.created_at`
      );

      if (result.rows.length === 0) {
        await client.query('ROLLBACK');
        log.info('No bookings eligible for payout');
        return { status: 'no_payouts', payouts: [] };
      }

      // Group by host with proper typing and validation
      const payoutsByHost = new Map<string, HostPayoutData>();

      for (const row of result.rows) {
        // Validate row data
        if (!row.amount_cents || row.amount_cents <= 0) {
          log.warn('Skipping booking with invalid amount', {
            booking_id: row.booking_id,
            amount_cents: row.amount_cents,
          });
          continue;
        }

        if (!row.host_payout_cents || row.host_payout_cents < 0) {
          log.warn('Skipping booking with invalid host payout', {
            booking_id: row.booking_id,
            host_payout_cents: row.host_payout_cents,
          });
          continue;
        }

        if (!payoutsByHost.has(row.host_id)) {
          payoutsByHost.set(row.host_id, {
            host_id: row.host_id,
            host_email: row.host_email,
            host_name: row.host_name,
            stripe_account_id: row.stripe_account_id,
            bookings: [],
            total_host_payout_cents: 0,
            total_platform_fee_cents: 0,
          });
        }

        const hostData = payoutsByHost.get(row.host_id)!;
        hostData.bookings.push({
          booking_id: row.booking_id,
          amount_cents: row.amount_cents,
          host_payout_cents: row.host_payout_cents,
          platform_fee_cents: row.platform_fee_cents,
        });
        hostData.total_host_payout_cents += row.host_payout_cents;
        hostData.total_platform_fee_cents += row.platform_fee_cents;
      }

      // Create payout records (one per host, not per booking)
      const payoutRecords: PayoutRecord[] = [];

      for (const [hostId, data] of payoutsByHost) {
        const payoutId = randomUUID();

        // Insert single payout record for host
        await client.query(
          `INSERT INTO payouts (
            payout_id,
            host_id,
            amount_cents,
            currency,
            status,
            stripe_account_id,
            booking_count,
            created_at,
            scheduled_for
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW() + INTERVAL '1 day')`,
          [
            payoutId,
            hostId,
            data.total_host_payout_cents,
            'USD',
            'pending',
            data.stripe_account_id,
            data.bookings.length,
          ]
        );

        // Batch insert all booking links for this payout
        if (data.bookings.length > 0) {
          const values = data.bookings.map((_, idx) => {
            const offset = idx * 3;
            return `($${offset + 1}, $${offset + 2}, $${offset + 3})`;
          }).join(',');

          const params = data.bookings.flatMap(booking => [
            payoutId,
            booking.booking_id,
            booking.host_payout_cents,
          ]);

          await client.query(
            `INSERT INTO payout_bookings (
              payout_id,
              booking_id,
              amount_cents
            ) VALUES ${values}`,
            params
          );
        }

        payoutRecords.push({
          payout_id: payoutId,
          host_id: hostId,
          host_email: data.host_email,
          host_name: data.host_name,
          booking_count: data.bookings.length,
          total_amount_cents: data.total_host_payout_cents,
          stripe_account_id: data.stripe_account_id,
        });

        log.info('Payout created for host', {
          payout_id: payoutId,
          host_id: hostId,
          booking_count: data.bookings.length,
          total_amount_cents: data.total_host_payout_cents,
        });
      }

      await client.query('COMMIT');

      log.info('Weekly payouts generated successfully', {
        host_count: payoutRecords.length,
        total_bookings: result.rows.length,
        total_amount_cents: payoutRecords.reduce((sum, p) => sum + p.total_amount_cents, 0),
      });

      return {
        status: 'success',
        payouts: payoutRecords,
      };

    } catch (error) {
      if (client) {
        await client.query('ROLLBACK');
      }
      log.error('Failed to generate payouts', error as Error);
      throw error;
    } finally {
      if (client) {
        client.release();
      }
    }
  }
}
