import type { AnalyticsEvent } from './types';

const listeners: Array<(event: AnalyticsEvent) => void> = [];

export const trackEvent = (event: AnalyticsEvent) => {
  if (process.env.NODE_ENV !== 'production') {
    console.debug('[analytics]', event);
  }
  listeners.forEach((listener) => listener(event));
};

export const onAnalyticsEvent = (callback: (event: AnalyticsEvent) => void) => {
  listeners.push(callback);
  return () => {
    const index = listeners.indexOf(callback);
    if (index >= 0) {
      listeners.splice(index, 1);
    }
  };
};
