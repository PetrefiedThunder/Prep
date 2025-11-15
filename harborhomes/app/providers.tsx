"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";

import { ActionableErrorFallback, ErrorBoundary } from "@/components/system/error-boundary";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { Toaster } from "@/components/ui/toaster";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(() => new QueryClient());

  return (
    <QueryClientProvider client={client}>
      <ErrorBoundary
        context="app/providers"
        fallback={({ reset }) => (
          <ActionableErrorFallback
            title="HarborHomes is temporarily unavailable"
            description="An unexpected error stopped the application. Try reloading the page or contact support so we can help."
            primaryActionLabel="Reload application"
            onPrimaryAction={() => {
              if (typeof window !== "undefined") {
                window.location.reload();
              }
            }}
            secondaryActionLabel="Contact support"
            secondaryActionHref="mailto:support@harborhomes.app"
            reset={reset}
          />
        )}
      >
        <ThemeProvider>
          {children}
          <Toaster />
        </ThemeProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
