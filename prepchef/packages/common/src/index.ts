import { z } from 'zod';
export { prepSecurityPlugin } from './security';
export type { PrepSecurityPluginOptions } from './security';

export const Money = z.object({ amount_cents: z.number().int(), currency: z.string().default('USD') });
export type Money = z.infer<typeof Money>;

export const BookingStatus = z.enum([
  'requested',
  'awaiting_docs',
  'payment_authorized',
  'confirmed',
  'active',
  'completed',
  'canceled',
  'no_show',
  'disputed'
]);
export type BookingStatus = z.infer<typeof BookingStatus>;

export const ApiError = (code: string, message: string, hint?: string) => ({
  code,
  message,
  ...(hint ? { hint } : {})
});
