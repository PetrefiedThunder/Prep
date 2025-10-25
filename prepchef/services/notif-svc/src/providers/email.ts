import { log } from '@prep/logger';
import { fetch } from 'undici';
import type { DeliveryReceipt, EmailPayload, EmailProvider } from '../types';

const SENDGRID_API_URL = 'https://api.sendgrid.com/v3/mail/send';

export interface SendGridEmailProviderOptions {
  fromEmail?: string;
}

export class SendGridEmailProvider implements EmailProvider {
  private readonly sentEmails: EmailPayload[] = [];
  private readonly fromEmail: string;

  constructor(options: SendGridEmailProviderOptions = {}) {
    this.fromEmail = options.fromEmail ?? 'no-reply@prep.kitchen';
  }

  async sendEmail(payload: EmailPayload): Promise<DeliveryReceipt> {
    this.sentEmails.push(payload);
    let detail = 'queued (simulated)';

    const apiKey = process.env.SENDGRID_API_KEY;
    if (apiKey) {
      try {
        const response = await fetch(SENDGRID_API_URL, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            from: { email: this.fromEmail },
            personalizations: [
              {
                to: [{ email: payload.to }],
                dynamic_template_data: payload.data ?? {}
              }
            ],
            subject: payload.subject,
            content: [
              {
                type: 'text/plain',
                value: payload.text
              },
              ...(payload.html
                ? [
                    {
                      type: 'text/html',
                      value: payload.html
                    }
                  ]
                : [])
            ],
            ...(payload.templateId ? { template_id: payload.templateId } : {})
          })
        });

        if (!response.ok) {
          detail = `sendgrid:${response.status}`;
          log.warn('SendGrid email delivery failed', {
            status: response.status,
            statusText: response.statusText
          });
        } else {
          detail = 'sendgrid:accepted';
        }
      } catch (error) {
        detail = 'sendgrid:error';
        log.error('Error sending email via SendGrid', { error });
      }
    } else if (process.env.MAILHOG_URL) {
      detail = 'mailhog:recorded';
      log.info('MailHog email queued', { to: payload.to, subject: payload.subject });
    } else {
      log.debug('Email delivery simulated (no provider configured)', {
        to: payload.to,
        subject: payload.subject
      });
    }

    return {
      channel: 'email',
      delivered: true,
      detail
    };
  }

  getSentEmails(): EmailPayload[] {
    return [...this.sentEmails];
  }

  clear(): void {
    this.sentEmails.length = 0;
  }
}
