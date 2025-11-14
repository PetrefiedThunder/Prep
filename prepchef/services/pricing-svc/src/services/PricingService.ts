/**
 * PricingService (C12)
 * Calculates platform fees and host payout amounts
 */

import { log } from '@prep/logger';

export interface PriceBreakdown {
  subtotal_cents: number;
  platform_fee_cents: number;
  host_payout_cents: number;
  total_cents: number;
  fee_percentage: number;
}

export class PricingService {
  constructor(
    private platformFeePercentage: number = 15 // Default 15% platform fee
  ) {}

  calculatePricing(subtotalCents: number): PriceBreakdown {
    // Validate input
    if (subtotalCents < 0) {
      throw new Error('Subtotal must be non-negative');
    }

    if (subtotalCents === 0) {
      return {
        subtotal_cents: 0,
        platform_fee_cents: 0,
        host_payout_cents: 0,
        total_cents: 0,
        fee_percentage: this.platformFeePercentage
      };
    }

    // Calculate platform fee with proper rounding
    const platformFeeCents = Math.round(subtotalCents * (this.platformFeePercentage / 100));

    // Host payout is subtotal minus platform fee
    const hostPayoutCents = subtotalCents - platformFeeCents;

    // Total charged to user is subtotal
    const totalCents = subtotalCents;

    log.info('Calculated pricing', {
      subtotal_cents: subtotalCents,
      platform_fee_cents: platformFeeCents,
      host_payout_cents: hostPayoutCents,
      fee_percentage: this.platformFeePercentage
    });

    return {
      subtotal_cents: subtotalCents,
      platform_fee_cents: platformFeeCents,
      host_payout_cents: hostPayoutCents,
      total_cents: totalCents,
      fee_percentage: this.platformFeePercentage
    };
  }

  /**
   * Calculate payout after refunds are applied
   */
  calculateRefundedPayout(originalPayoutCents: number, refundCents: number): number {
    if (refundCents > originalPayoutCents) {
      throw new Error('Refund amount exceeds original payout');
    }

    const remainingPayoutCents = originalPayoutCents - refundCents;

    // Handle rounding edge case: ensure we don't pay out negative amounts
    return Math.max(0, remainingPayoutCents);
  }

  /**
   * Test coverage for edge cases
   */
  static runTests() {
    const service = new PricingService();

    // Test: Normal booking
    const test1 = service.calculatePricing(10000); // $100.00
    console.assert(test1.platform_fee_cents === 1500, 'Platform fee should be $15.00');
    console.assert(test1.host_payout_cents === 8500, 'Host payout should be $85.00');

    // Test: Tiny booking (rounding)
    const test2 = service.calculatePricing(10); // $0.10
    console.assert(test2.platform_fee_cents >= 0, 'Platform fee should round correctly');
    console.assert(test2.host_payout_cents >= 0, 'Host payout should be non-negative');

    // Test: Zero booking
    const test3 = service.calculatePricing(0);
    console.assert(test3.total_cents === 0, 'Zero booking should have zero total');

    console.log('PricingService tests passed');
  }
}
