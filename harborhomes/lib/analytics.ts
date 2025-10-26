import type { AnalyticsEvent } from "./types";

export function track(event: AnalyticsEvent) {
  if (process.env.NODE_ENV !== "production") {
    console.info("[analytics]", event);
  }
}
