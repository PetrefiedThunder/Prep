"use client";

import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
    console.log("Sign in", values);
  };

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-6 py-12">
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
      <Button variant="ghost" className="w-full rounded-full">
        Send magic link
      </Button>
    </div>
  );
}
