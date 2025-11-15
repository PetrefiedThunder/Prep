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
  password: z.string().min(8),
  name: z.string().min(1)
});

type FormValues = z.infer<typeof schema>;

export default function SignUpPage() {
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const [strength, setStrength] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (values: FormValues) => {
    setError(null);

    try {
      console.info("Sign up attempt", values);
      throw new Error("Account creation is disabled in MVP");
    } catch (error) {
      const normalized = normalizeError(error, "Sign-up failed");
      reportClientError(normalized, "auth/sign-up:onSubmit");
      setError("Account creation is paused while we finish onboarding. Reach out and we'll get you on the waitlist.");
    }
  };

  return (
    <ErrorBoundary
      context="app/(site)/auth/sign-up/page"
      fallback={({ reset }) => (
        <ActionableErrorFallback
          title="Account creation is paused"
          description="We're finalising onboarding and compliance workflows. Check back soon or email us to reserve a spot."
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
          title="Sign-up in maintenance"
          description="We're manually onboarding early partners. Submit the form to join the waitlist once the flow is live."
          actionLabel="Email support"
          onAction={() => {
            if (typeof window !== "undefined") {
              window.location.href = "mailto:support@harborhomes.app";
            }
          }}
        />
        <h1 className="text-3xl font-semibold">Create a HarborHomes account</h1>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="text-xs font-semibold text-muted-ink">Name</label>
            <Input {...register("name")} />
            {errors.name && <p className="text-xs text-red-600">{errors.name.message}</p>}
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-ink">Email</label>
            <Input type="email" {...register("email")} />
            {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-ink">Password</label>
            <Input
              type="password"
              {...register("password")}
              onChange={(event) => {
                const value = event.target.value;
                setStrength(Math.min(100, value.length * 10));
                event.target.dispatchEvent(new Event("input", { bubbles: true }));
              }}
            />
            <div className="mt-2 h-2 w-full rounded-full bg-border">
              <div className="h-full rounded-full bg-brand" style={{ width: `${strength}%` }} />
            </div>
            {errors.password && <p className="text-xs text-red-600">Use at least 8 characters</p>}
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <Button type="submit" className="w-full rounded-full">
            Sign up
          </Button>
        </form>
      </div>
    </ErrorBoundary>
  );
}
