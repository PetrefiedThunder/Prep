'use client';

import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  retryCount: number;
}

/**
 * ErrorBoundary Component
 *
 * Catches JavaScript errors anywhere in the child component tree and displays a fallback UI.
 * Includes retry mechanism and optional error details display.
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private maxRetries = 3;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Log error to error reporting service
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    } else {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // In production, send to error tracking service (e.g., Sentry)
    if (process.env.NODE_ENV === 'production') {
      // Example: Sentry.captureException(error, { extra: errorInfo });
    }
  }

  handleRetry = () => {
    const { retryCount } = this.state;

    if (retryCount < this.maxRetries) {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: retryCount + 1
      });
    } else {
      // Max retries reached, reload page
      window.location.reload();
    }
  };

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    });
  };

  render() {
    const { hasError, error, errorInfo, retryCount } = this.state;
    const { children, fallback, showDetails = false } = this.props;

    if (hasError) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Default error UI
      return (
        <div className="flex min-h-[400px] items-center justify-center px-4 py-16">
          <div className="w-full max-w-md">
            <div className="rounded-xl border border-error/20 bg-error-light p-8 text-center shadow-lg">
              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-error/10">
                <AlertCircle className="h-8 w-8 text-error" />
              </div>

              <h2 className="mb-2 text-2xl font-semibold text-ink">Something went wrong</h2>

              <p className="mb-6 text-ink-muted">
                {retryCount >= this.maxRetries
                  ? "We've tried multiple times to recover. Please refresh the page."
                  : 'An unexpected error occurred. You can try again or refresh the page.'}
              </p>

              {showDetails && error && (
                <details className="mb-6 rounded-lg bg-surface p-4 text-left">
                  <summary className="cursor-pointer text-sm font-medium text-ink hover:text-brand">
                    Error Details
                  </summary>
                  <div className="mt-3 space-y-2">
                    <div className="rounded bg-surface-sunken p-3">
                      <p className="mb-1 text-xs font-semibold text-ink-muted">Error Message:</p>
                      <p className="font-mono text-xs text-error-dark">{error.message}</p>
                    </div>
                    {errorInfo && (
                      <div className="rounded bg-surface-sunken p-3">
                        <p className="mb-1 text-xs font-semibold text-ink-muted">Component Stack:</p>
                        <pre className="overflow-auto font-mono text-xs text-ink-subtle">
                          {errorInfo.componentStack}
                        </pre>
                      </div>
                    )}
                  </div>
                </details>
              )}

              <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
                <Button onClick={this.handleRetry} className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  {retryCount >= this.maxRetries ? 'Reload Page' : `Try Again ${retryCount > 0 ? `(${retryCount}/${this.maxRetries})` : ''}`}
                </Button>

                {retryCount > 0 && retryCount < this.maxRetries && (
                  <Button variant="secondary" onClick={this.handleReset}>
                    Reset
                  </Button>
                )}
              </div>

              {process.env.NODE_ENV === 'development' && (
                <div className="mt-4 text-xs text-ink-muted">
                  Development mode: Check console for detailed error information
                </div>
              )}
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

/**
 * Functional wrapper for error boundaries in specific contexts
 */
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name || 'Component'})`;

  return WrappedComponent;
};
