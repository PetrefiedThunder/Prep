import * as React from "react";
import { format, parseISO } from "date-fns";

export type TodayItemState = "ok" | "warn" | "err";

export interface TodayItem {
  title: string;
  scope: string;
  detail: string;
  state: TodayItemState;
}

export function TodayList({ items }: { items: TodayItem[] }) {
  return (
    <ul className="space-y-[calc(var(--baseline)*1.5)]" aria-label="Today's compliance items">
      {items.map((it, i) => (
        <li key={i} className="font-sans">
          <div className="text-[color:var(--ink-9)]">
            <span className="font-medium">{it.title}</span>{" "}
            <span className="opacity-70">({it.scope})</span>
          </div>
          <div className="text-[color:var(--ink-8)] text-[1rem] leading-[1.5] mt-[calc(var(--baseline)*0.5)]">
            {it.detail}
            {it.state === "ok" && <span className="ml-2 text-[color:var(--signal-green)]">Verified</span>}
            {it.state === "warn" && <span className="ml-2 text-[color:var(--signal-amber)]">Attention</span>}
            {it.state === "err" && <span className="ml-2 text-[color:var(--signal-red)] font-medium">Action required</span>}
          </div>
        </li>
      ))}
      {items.length === 0 && <li className="text-[color:var(--ink-8)]">No items today.</li>}
    </ul>
  );
}

export interface HorizonItem {
  id: string;
  what: string;
  jurisdiction: string;
  eta: string;
  probability: number;
  impact: string;
  source: string;
}

export function HorizonTimeline({ items }: { items: HorizonItem[] }) {
  if (!items?.length) return <p className="font-sans text-[color:var(--ink-8)]">Horizon is clear.</p>;
  const sorted = [...items].sort((a, b) => a.eta.localeCompare(b.eta));

  return (
    <div className="relative pl-[calc(var(--baseline)*2)]">
      <div aria-hidden className="absolute left-[6px] top-0 bottom-0 w-px bg-[color:var(--ink-2)]" />
      <ul className="space-y-[calc(var(--baseline)*2)]">
        {sorted.map((it) => (
          <li key={it.id} className="font-sans relative">
            <span aria-hidden className="absolute -left-[3px] top-[8px] inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--signal-amber)]" />
            <div className="text-[color:var(--ink-9)] font-medium text-[1.125rem] tracking-[-0.005em]">
              {it.what}
            </div>
            <div className="text-[color:var(--ink-8)] text-[1rem] mt-[calc(var(--baseline)*0.5)]">
              <span className="mr-3"><strong>Jurisdiction:</strong> {it.jurisdiction}</span>
              <span className="mr-3"><strong>Effective:</strong> {format(parseISO(it.eta), "PPP")}</span>
              <span className="mr-3"><strong>Probability:</strong> {(it.probability * 100).toFixed(0)}%</span>
            </div>
            <div className="text-[color:var(--ink-8)] mt-[calc(var(--baseline)*0.5)]">{it.impact}</div>
            <div className="mt-[calc(var(--baseline)*0.5)]">
              <a
                className="text-[color:var(--ink-9)] underline underline-offset-2 focus:outline-none focus:ring-2 focus:ring-[color:var(--ink-9)] focus:ring-offset-2"
                href={`/source?eli=${encodeURIComponent(it.source)}`}
              >
                View Source ({it.source.split("/").pop()})
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export interface CompliancePassportItem {
  label: string;
  scope: string;
  note?: string;
}

export interface CompliancePassportProps {
  items: CompliancePassportItem[];
  horizonClear: boolean;
  horizonHref?: string;
}

export function CompliancePassport({ items, horizonClear, horizonHref = "/host/compliance#horizon" }: CompliancePassportProps) {
  return (
    <section className="font-sans text-[1rem] leading-[1.5] text-[color:var(--ink-8)]">
      <h3 className="mb-[calc(var(--baseline)*1)] font-medium text-[color:var(--ink-9)] text-[1.125rem] tracking-[-0.005em]">
        Compliance Passport
      </h3>
      <ul className="space-y-[calc(var(--baseline)*0.5)]">
        {items.map((it, i) => (
          <li key={i} className="flex items-baseline gap-2">
            <span aria-hidden className="inline-block h-[10px] w-[10px] rounded-full bg-[color:var(--signal-green)]" />
            <span className="text-[color:var(--ink-9)]">{it.label}</span>
            <span className="opacity-70">({it.scope})</span>
            {it.note && <span className="ml-2">{it.note}</span>}
          </li>
        ))}
      </ul>
      <hr className="my-[calc(var(--baseline)*1.5)] border-0 h-px bg-[color:var(--ink-2)]" />
      {horizonClear ? (
        <div className="flex items-baseline gap-2">
          <span aria-hidden className="inline-block h-[10px] w-[10px] rounded-full bg-[color:var(--signal-green)]" />
          <span className="text-[color:var(--ink-9)] font-medium">Horizon Clear</span>
          <span className="opacity-70">No upcoming changes for your dates.</span>
        </div>
      ) : (
        <div className="flex items-baseline gap-2">
          <span aria-hidden className="inline-block h-[10px] w-[10px] rounded-full bg-[color:var(--signal-amber)]" />
          <span className="text-[color:var(--ink-9)] font-medium">Horizon Warning</span>
          <a className="underline underline-offset-2" href={horizonHref}>
            See details
          </a>
        </div>
      )}
    </section>
  );
}
