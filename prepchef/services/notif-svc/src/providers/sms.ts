import { log } from '@prep/logger';
import { fetch } from 'undici';
import type { DeliveryReceipt, SmsPayload, SmsProvider } from '../types';

const TWILIO_API_BASE = 'https://api.twilio.com/2010-04-01';

export interface TwilioSmsProviderOptions {
  fromNumber?: string;
}

export class TwilioSmsProvider implements SmsProvider {
  private readonly sentMessages: SmsPayload[] = [];
  private readonly fromNumber: string;

  constructor(options: TwilioSmsProviderOptions = {}) {
    this.fromNumber = options.fromNumber ?? process.env.TWILIO_FROM_NUMBER ?? '+15555555555';
  }

  async sendSms(payload: SmsPayload): Promise<DeliveryReceipt> {
    this.sentMessages.push(payload);
    const accountSid = process.env.TWILIO_ACCOUNT_SID;
    const authToken = process.env.TWILIO_AUTH_TOKEN;
    let detail = 'queued (simulated)';

    if (accountSid && authToken) {
      try {
        const response = await fetch(
          `${TWILIO_API_BASE}/Accounts/${accountSid}/Messages.json`,
          {
            method: 'POST',
            headers: {
              Authorization: `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`,
              'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
              From: this.fromNumber,
              To: payload.to,
              Body: payload.body
            }).toString()
          }
        );

        if (!response.ok) {
          detail = `twilio:${response.status}`;
          log.warn('Twilio SMS delivery failed', {
            status: response.status,
            statusText: response.statusText
          });
        } else {
          detail = 'twilio:accepted';
        }
      } catch (error) {
        detail = 'twilio:error';
        log.error('Error sending SMS via Twilio', { error });
      }
    } else {
      log.debug('SMS delivery simulated (no provider configured)', {
        to: payload.to
      });
    }

    return {
      channel: 'sms',
      delivered: true,
      detail
    };
  }

  getSentMessages(): SmsPayload[] {
    return [...this.sentMessages];
  }

  clear(): void {
    this.sentMessages.length = 0;
  }
}
