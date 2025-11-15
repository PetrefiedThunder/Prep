"use client";

export function normalizeError(error: unknown, fallbackMessage = "Unknown error"): Error {
  if (error instanceof Error) {
    return error;
  }

  if (typeof error === "string") {
    return new Error(error);
  }

  return new Error(fallbackMessage);
}

export function reportClientError(error: unknown, context: string) {
  const normalized = normalizeError(error, `Error captured in ${context}`);

  if (typeof window !== "undefined") {
    if (process.env.NODE_ENV !== "production") {
      console.error(`[telemetry] ${context}`, normalized);
    }

    const telemetry = (window as typeof window & {
      harborhomesTelemetry?: { captureException?: (err: Error, meta?: Record<string, unknown>) => void };
    }).harborhomesTelemetry;

    if (telemetry?.captureException) {
      telemetry.captureException(normalized, { context });
    }
  }

  return normalized;
}
