"use client";

import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { ActionableErrorFallback, ErrorBoundary } from "@/components/system/error-boundary";
import { MaintenanceBanner } from "@/components/system/maintenance-banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { normalizeError, reportClientError } from "@/lib/telemetry";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(6)
});

type FormValues = z.infer<typeof schema>;

export default function SignInPage() {
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = (values: FormValues) => {
    setError(null);

    try {
      console.info("Sign in attempt", values);
      throw new Error("Authentication service is disabled in MVP");
    } catch (error) {
      const normalized = normalizeError(error, "Sign-in failed");
      reportClientError(normalized, "auth/sign-in:onSubmit");
      setError("Sign-in is currently under maintenance. Please use the product demo or try again soon.");
    }
  };

  const handleMagicLink = () => {
    try {
      throw new Error("Magic link delivery is not configured");
    } catch (error) {
      const normalized = normalizeError(error, "Magic link unavailable");
      reportClientError(normalized, "auth/sign-in:magic-link");
      setError("Magic links are paused while we finish setup. Email support@harborhomes.app for access.");
    }
  };

  return (
    <ErrorBoundary
      context="app/(site)/auth/sign-in/page"
      fallback={({ reset }) => (
        <ActionableErrorFallback
          title="Sign-in isn't ready yet"
          description="We're wrapping up the authentication flow. In the meantime you can browse the demo experience."
          primaryActionLabel="Reload"
          onPrimaryAction={() => {
            reset();
            if (typeof window !== "undefined") {
              window.location.reload();
            }
          }}
          secondaryActionLabel="Email support"
          secondaryActionHref="mailto:support@harborhomes.app"
          reset={reset}
        />
      )}
    >
      <div className="mx-auto flex max-w-md flex-col gap-6 px-6 py-12">
        <MaintenanceBanner
          title="Authentication in maintenance"
          description="We're finalising secure sign-in. For early access, contact support and we'll get you set up manually."
          actionLabel="Contact support"
          onAction={() => {
            if (typeof window !== "undefined") {
              window.location.href = "mailto:support@harborhomes.app";
            }
          }}
        />
        <h1 className="text-3xl font-semibold">Welcome back</h1>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="text-xs font-semibold text-muted-ink">Email</label>
            <Input type="email" {...register("email")} />
            {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-ink">Password</label>
            <Input type="password" {...register("password")} />
            {errors.password && <p className="text-xs text-red-600">At least 6 characters</p>}
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <Button type="submit" className="w-full rounded-full">
            Sign in
          </Button>
        </form>
        <Button variant="ghost" className="w-full rounded-full" onClick={handleMagicLink}>
          Send magic link
        </Button>
      </div>
    </ErrorBoundary>
  );
}
