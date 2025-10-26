"use client";

import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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

  const onSubmit = (values: FormValues) => {
    console.log("Sign up", values);
  };

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-6 py-12">
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
        <Button type="submit" className="w-full rounded-full">
          Sign up
        </Button>
      </form>
    </div>
  );
}
