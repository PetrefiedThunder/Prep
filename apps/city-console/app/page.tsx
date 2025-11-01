import React from "react";
const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8080";
async function get(city: string, path: string) {
  const r = await fetch(`${API}/city/${encodeURIComponent(city)}/${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} ${city} ${r.status}`);
  return r.json();
}
export default async function Page() {
  const cities = ["sf","joshua tree"];
  const data = await Promise.all(cities.map(async c => ({
    city: c,
    fees: await get(c,"fees"),
    reqs: await get(c,"requirements"),
  })));
  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <h1 className="text-2xl font-bold">City Console — Read-only</h1>
        {data.map(({city,fees,reqs}) => (
          <div key={city} className="rounded-2xl border bg-white p-4 space-y-3">
            <h2 className="text-xl font-semibold">{city.toUpperCase()}</h2>
            <div className="grid md:grid-cols-3 gap-3">
              <div className="rounded-xl border p-3">
                <div className="text-xs uppercase text-slate-500">Blocking requirements</div>
                <div className="text-xl font-bold">{reqs.validation?.blocking_count ?? 0}</div>
              </div>
              <div className="rounded-xl border p-3">
                <div className="text-xs uppercase text-slate-500">One-time fees</div>
                <div className="text-xl font-bold">{(fees.totals?.one_time_cents ?? 0)/100}</div>
              </div>
              <div className="rounded-xl border p-3">
                <div className="text-xs uppercase text-slate-500">Recurring annualized</div>
                <div className="text-xl font-bold">{(fees.totals?.recurring_annualized_cents ?? 0)/100}</div>
              </div>
            </div>
            <div className="text-sm text-slate-600">Requirements: {reqs.requirements?.length ?? 0} • Fees: {fees.fees?.length ?? 0}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
