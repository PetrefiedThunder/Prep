import React from "react";
import { FeeCard, RequirementsList, PermitBadge, type FeesResponse, type RequirementsBundleResponse } from "@/components/prep";

const API = process.env.NEXT_PUBLIC_API_BASE!;

async function fetchFees(city: string): Promise<FeesResponse> {
  const r = await fetch(`${API}/city/${encodeURIComponent(city)}/fees`, { cache: "no-store" });
  if (!r.ok) throw new Error(`fees: ${city} ${r.status}`);
  return r.json();
}
async function fetchReqs(city: string): Promise<RequirementsBundleResponse> {
  const r = await fetch(`${API}/city/${encodeURIComponent(city)}/requirements`, { cache: "no-store" });
  if (!r.ok) throw new Error(`requirements: ${city} ${r.status}`);
  return r.json();
}

export default async function Page() {
  const [sfFees, sfReqs, jtFees, jtReqs] = await Promise.all([fetchFees("sf"), fetchReqs("sf"), fetchFees("joshua tree"), fetchReqs("joshua tree")]);
  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Prep — SF Bay Area & Joshua Tree</h1>
          <div className="flex gap-3">
            <PermitBadge isValid={sfReqs.validation.is_valid} blockingCount={sfReqs.validation.blocking_count} jurisdictionLabel="San Francisco" />
            <PermitBadge isValid={jtReqs.validation.is_valid} blockingCount={jtReqs.validation.blocking_count} jurisdictionLabel="Joshua Tree" />
          </div>
        </header>
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">San Francisco</h2>
          <FeeCard data={sfFees} />
          <RequirementsList data={sfReqs} partyFilter="all" />
        </section>
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Joshua Tree</h2>
          <FeeCard data={jtFees} />
          <RequirementsList data={jtReqs} partyFilter="all" />
        </section>
      </div>
    </div>
  );
}
