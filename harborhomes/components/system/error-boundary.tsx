"use client";

import * as React from "react";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { reportClientError, normalizeError } from "@/lib/telemetry";

type ErrorBoundaryProps = {
  children: React.ReactNode;
  /**
   * Optional context describing where the boundary is mounted. Used for telemetry.
   */
  context?: string;
  fallback?: React.ReactNode | ((args: { error?: Error; reset: () => void }) => React.ReactNode);
  onError?: (error: Error, info: React.ErrorInfo) => void;
};

type ErrorBoundaryState = {
  hasError: boolean;
  error?: Error;
};

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    hasError: false,
    error: undefined
  };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    const context = this.props.context ?? "error-boundary";
    const normalized = normalizeError(error, `Unhandled error in ${context}`);
    reportClientError(normalized, context);

    if (this.props.onError) {
      this.props.onError(normalized, info);
    }
  }

  private reset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      if (typeof this.props.fallback === "function") {
        return this.props.fallback({ error: this.state.error, reset: this.reset });
      }

      return this.props.fallback ?? (
        <ActionableErrorFallback
          title="Something went wrong"
          description="Try reloading the page. If the problem continues, reach out to the HarborHomes team."
          primaryActionLabel="Reload"
          onPrimaryAction={() => {
            this.reset();
            if (typeof window !== "undefined") {
              window.location.reload();
            }
          }}
          secondaryActionLabel="Contact support"
          secondaryActionHref="mailto:support@harborhomes.app"
        />
      );
    }

    return this.props.children;
  }
}

type ActionableErrorFallbackProps = {
  title: string;
  description: string;
  primaryActionLabel: string;
  onPrimaryAction?: () => void;
  secondaryActionLabel?: string;
  secondaryActionHref?: string;
  reset?: () => void;
  errorDetails?: string;
};

export function ActionableErrorFallback({
  title,
  description,
  primaryActionLabel,
  onPrimaryAction,
  secondaryActionLabel,
  secondaryActionHref,
  reset,
  errorDetails
}: ActionableErrorFallbackProps) {
  const handlePrimaryAction = () => {
    if (reset) {
      reset();
    }

    if (onPrimaryAction) {
      onPrimaryAction();
    }
  };

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-4 rounded-3xl border border-border bg-white p-8 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-100">
        <AlertTriangle className="h-6 w-6 text-amber-600" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-ink">{title}</h2>
        <p className="text-sm text-muted-ink">{description}</p>
        {errorDetails ? <p className="text-xs text-muted-ink">{errorDetails}</p> : null}
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
        <Button className="flex-1 sm:flex-none" onClick={handlePrimaryAction}>
          {primaryActionLabel}
        </Button>
        {secondaryActionLabel && secondaryActionHref ? (
          <Button variant="outline" className="flex-1 sm:flex-none" asChild>
            <a href={secondaryActionHref}>{secondaryActionLabel}</a>
          </Button>
        ) : null}
      </div>
    </div>
  );
}
