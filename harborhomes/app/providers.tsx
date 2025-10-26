"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { Toaster } from "@/components/ui/toaster";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(() => new QueryClient());

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        {children}
        <Toaster />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
