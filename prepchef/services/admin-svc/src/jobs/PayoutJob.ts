/**
 * Host Payout Job (B9)
 * Aggregates confirmed bookings into weekly payouts
 */

import { Pool } from 'pg';
import { log } from '@prep/logger';
import { createObjectCsvWriter } from 'csv-writer';
import { randomUUID } from 'crypto';

export class PayoutService {
  constructor(private db: Pool) {}

  async generateWeeklyPayouts(): Promise<string> {
    const payoutId = randomUUID();

    try {
      // Find all confirmed bookings from last 7 days that don't have a payout
      const result = await this.db.query(
        `
        SELECT
          b.booking_id,
          b.kitchen_id,
          b.user_id,
          b.amount_cents,
          b.created_at,
          k.host_id,
          k.host_email,
          k.host_name
        FROM bookings b
        JOIN kitchens k ON b.kitchen_id = k.kitchen_id
        WHERE b.status = 'confirmed'
          AND b.created_at >= NOW() - INTERVAL '7 days'
          AND NOT EXISTS (
            SELECT 1 FROM payouts p
            WHERE p.booking_id = b.booking_id
          )
        ORDER BY k.host_id, b.created_at
        `
      );

      if (result.rows.length === 0) {
        log.info('No bookings to payout');
        return '';
      }

      // Group by host
      const payoutsByHost = result.rows.reduce((acc: any, row: any) => {
        const hostId = row.host_id;
        if (!acc[hostId]) {
          acc[hostId] = {
            host_id: hostId,
            host_email: row.host_email,
            host_name: row.host_name,
            bookings: [],
            total_cents: 0
          };
        }
        acc[hostId].bookings.push(row);
        acc[hostId].total_cents += row.amount_cents || 0;
        return acc;
      }, {});

      // Create payout records
      const csvRows = [];

      for (const [hostId, data] of Object.entries(payoutsByHost)) {
        const payoutAmount = (data as any).total_cents;

        // Insert payout record
        for (const booking of (data as any).bookings) {
          await this.db.query(
            `INSERT INTO payouts (
              payout_id,
              booking_id,
              host_id,
              amount_cents,
              status,
              created_at
            ) VALUES ($1, $2, $3, $4, $5, NOW())`,
            [randomUUID(), booking.booking_id, hostId, payoutAmount, 'pending']
          );
        }

        csvRows.push({
          host_id: hostId,
          host_email: (data as any).host_email,
          host_name: (data as any).host_name,
          booking_count: (data as any).bookings.length,
          total_amount_usd: (payoutAmount / 100).toFixed(2)
        });
      }

      // Generate CSV for finance
      const csvPath = `/tmp/payouts-${payoutId}.csv`;
      const csvWriter = createObjectCsvWriter({
        path: csvPath,
        header: [
          { id: 'host_id', title: 'Host ID' },
          { id: 'host_email', title: 'Email' },
          { id: 'host_name', title: 'Name' },
          { id: 'booking_count', title: 'Bookings' },
          { id: 'total_amount_usd', title: 'Amount (USD)' }
        ]
      });

      await csvWriter.writeRecords(csvRows);

      log.info('Weekly payouts generated', {
        payout_id: payoutId,
        host_count: csvRows.length,
        csv_path: csvPath
      });

      return csvPath;

    } catch (error) {
      log.error('Failed to generate payouts', error);
      throw error;
    }
  }
}
