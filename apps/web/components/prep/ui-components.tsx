import React, { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, AlertTriangle, Wallet, FileText, Layers } from "lucide-react";

export type FeeItem = {
  name: string;
  amount_cents: number;
  kind: "one_time" | "recurring" | "incremental";
  cadence?: "annual" | "semi_annual" | "quarterly" | "monthly" | "per_permit" | "per_inspection" | "per_application" | null;
  unit?: string | null;
  tier_min_inclusive?: number | null;
  tier_max_inclusive?: number | null;
};
export type FeesResponse = {
  jurisdiction: string;
  paperwork: string[];
  fees: FeeItem[];
  totals: {
    one_time_cents: number;
    recurring_annualized_cents: number;
    incremental_fee_count: number;
  };
  validation: { is_valid: boolean; issues: string[] };
};
export type Requirement = {
  id: string;
  title: string;
  description?: string;
  applies_to: "kitchen_operator" | "food_business" | "marketplace_operator" | "platform_developer";
  req_type:
    | "license"
    | "permit"
    | "inspection"
    | "insurance"
    | "training"
    | "posting"
    | "tax"
    | "platform_policy"
    | "data_protection"
    | "accessibility";
  authority: string;
  citation?: string | null;
  source_url?: string | null;
  paperwork_ids?: string[];
  fee_refs?: string[];
  cadence?: "one_time" | "annual" | "semi_annual" | "quarterly" | "monthly" | "per_event";
  renewal_month?: number | null;
  severity: "blocking" | "conditional" | "advisory";
  notes?: string | null;
};
export type RequirementsBundleResponse = {
  jurisdiction: string;
  version: string;
  requirements: Requirement[];
  change_candidates: Array<{
    id: string;
    title: string;
    action: "lobby_exemption" | "seek_variance" | "pilot_waiver" | "amend_policy" | "clarify_guidance";
    impact: "low" | "medium" | "high";
  }>;
  validation: {
    is_valid: boolean;
    issues: string[];
    counts_by_party: Record<string, number>;
    blocking_count: number;
    has_fee_links: boolean;
  };
};
const money = (cents: number, currency = "USD", locale = undefined) =>
  new Intl.NumberFormat(locale, { style: "currency", currency }).format(cents / 100);
const Pill: React.FC<{ intent: "ok" | "warn" | "error" | "info"; children: React.ReactNode }> = ({ intent, children }) => {
  const tone =
    intent === "ok"
      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
      : intent === "warn"
      ? "bg-amber-50 text-amber-800 border-amber-200"
      : intent === "error"
      ? "bg-rose-50 text-rose-800 border-rose-200"
      : "bg-sky-50 text-sky-800 border-sky-200";
  return <span className={`px-2 py-1 rounded-full text-xs border ${tone}`}>{children}</span>;
};
export const PermitBadge: React.FC<{ isValid: boolean; blockingCount?: number; jurisdictionLabel?: string }> = ({
  isValid,
  blockingCount = 0,
  jurisdictionLabel,
}) => {
  return (
    <div className="inline-flex items-center gap-2 rounded-2xl border px-3 py-1.5 bg-white shadow-sm">
      {isValid ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
      ) : blockingCount > 0 ? (
        <AlertTriangle className="h-4 w-4 text-amber-600" />
      ) : (
        <XCircle className="h-4 w-4 text-rose-600" />
      )}
      <span className="text-sm font-medium">
        {jurisdictionLabel || "Jurisdiction"}: {isValid ? "Ready" : blockingCount > 0 ? "Action needed" : "Invalid"}
      </span>
      {!isValid && <span className="text-xs text-slate-500">{blockingCount} blocking</span>}
    </div>
  );
};
export const FeeCard: React.FC<{ data: FeesResponse; currency?: string; locale?: string }> = ({ data, currency = "USD", locale }) => {
  const oneTime = money(data.totals.one_time_cents, currency, locale);
  const recurring = money(data.totals.recurring_annualized_cents, currency, locale);
  const incrementalCount = data.totals.incremental_fee_count;
  const grouped = useMemo(() => {
    const g: Record<string, FeeItem[]> = { one_time: [], recurring: [], incremental: [] };
    for (const f of data.fees) g[f.kind].push(f);
    return g;
  }, [data]);
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-slate-600" />
            <h3 className="text-lg font-semibold">Fees — {data.jurisdiction.replace("_", " ")}</h3>
          </div>
          {data.validation.is_valid ? <Pill intent="ok">Validated</Pill> : <Pill intent="warn">Check {data.validation.issues.length} issues</Pill>}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-xl border p-3">
            <div className="text-xs uppercase text-slate-500">One-time</div>
            <div className="text-xl font-bold">{oneTime}</div>
          </div>
          <div className="rounded-xl border p-3">
            <div className="text-xs uppercase text-slate-500">Recurring (annualized)</div>
            <div className="text-xl font-bold">{recurring}</div>
          </div>
          <div className="rounded-xl border p-3">
            <div className="text-xs uppercase text-slate-500">Incremental items</div>
            <div className="text-xl font-bold">{incrementalCount}</div>
          </div>
        </div>
        <div className="space-y-2">
          <h4 className="text-sm font-semibold flex items-center gap-2">
            <Layers className="h-4 w-4" />
            Breakdown
          </h4>
          <div className="grid md:grid-cols-3 gap-3">
            {["one_time", "recurring", "incremental"].map((k) => (
              <div key={k} className="rounded-xl border p-3">
                <div className="text-xs uppercase text-slate-500 mb-2">{k.replace("_", " ")}</div>
                <ul className="space-y-1">
                  {grouped[k as keyof typeof grouped].map((f) => (
                    <li key={f.name} className="flex items-center justify-between text-sm">
                      <span className="truncate mr-2">{f.name}</span>
                      <span className="font-medium">{money(f.amount_cents, currency, locale)}</span>
                    </li>
                  ))}
                  {grouped[k as keyof typeof grouped].length === 0 && <div className="text-xs text-slate-400">None</div>}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div className="pt-2">
          <div className="text-xs text-slate-500">Paperwork</div>
          <div className="flex flex-wrap gap-2 mt-1">
            {data.paperwork.map((p) => (
              <Badge key={p} variant="secondary" className="rounded-full">
                <FileText className="h-3 w-3 mr-1" /> {p}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
export const RequirementsList: React.FC<{
  data: RequirementsBundleResponse;
  partyFilter?: Requirement["applies_to"] | "all";
}> = ({ data, partyFilter = "all" }) => {
  const [q, setQ] = useState("");
  const items = useMemo(() => {
    return data.requirements
      .filter((r) => partyFilter === "all" || r.applies_to === partyFilter)
      .filter((r) => (q ? (r.title + (r.description || "") + r.authority + (r.citation || "")).toLowerCase().includes(q.toLowerCase()) : true));
  }, [data, partyFilter, q]);
  const severityTone = (s: Requirement["severity"]) =>
    s === "blocking"
      ? "bg-rose-50 text-rose-700 border-rose-200"
      : s === "conditional"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-slate-50 text-slate-700 border-slate-200";
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search requirements…"
          className="w-full rounded-xl border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
        />
        <Pill intent="info">{items.length} items</Pill>
      </div>
      <div className="grid gap-3">
        {items.map((r) => (
          <div key={r.id} className="rounded-2xl border p-4 bg-white shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="text-base font-semibold">{r.title}</div>
                <div className="text-sm text-slate-600">{r.description || ""}</div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <span className={`px-2 py-0.5 rounded-full text-xs border ${severityTone(r.severity)}`}>{r.severity}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs border bg-slate-50 text-slate-700 border-slate-200">{r.req_type}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs border bg-slate-50 text-slate-700 border-slate-200">{r.applies_to}</span>
                  {r.cadence && <span className="px-2 py-0.5 rounded-full text-xs border bg-slate-50 text-slate-700 border-slate-200">{r.cadence}</span>}
                </div>
                <div className="text-xs text-slate-500">
                  Authority: {r.authority}
                  {r.citation ? ` • ${r.citation}` : ""}
                </div>
              </div>
              <div className="shrink-0 flex flex-col items-end gap-2">
                {r.source_url && (
                  <a className="text-xs text-sky-700 underline" href={r.source_url} target="_blank" rel="noreferrer">
                    Source
                  </a>
                )}
                <Button variant="secondary" size="sm">
                  View details
                </Button>
              </div>
            </div>
          </div>
        ))}
        {items.length === 0 && <div className="text-sm text-slate-500">No matching requirements.</div>}
      </div>
    </div>
  );
};
