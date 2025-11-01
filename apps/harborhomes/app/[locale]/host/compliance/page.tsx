import "../../../../styles/compliance.theme.css";

import { Body, Divider, H1, H2, PageGrid, Section, SignalBar } from "./Primitives";
import {
  CompliancePassport,
  type CompliancePassportItem,
  HorizonTimeline,
  type HorizonItem,
  TodayList,
  type TodayItem
} from "./components";

const TODAY_ITEMS: TodayItem[] = [
  {
    title: "Kitchen permit self-certification",
    scope: "San Francisco DPH",
    detail: "Upload the signed self-certification for prep kitchen 102 before 17:00.",
    state: "warn"
  },
  {
    title: "Fire extinguisher inspection",
    scope: "SFFD",
    detail: "Document the quarterly inspection log and archive the receipt.",
    state: "ok"
  },
  {
    title: "Short-term rental tax remittance",
    scope: "California CDTFA",
    detail: "Confirm remittance confirmation ID with accounting.",
    state: "err"
  }
];

const HORIZON_ITEMS: HorizonItem[] = [
  {
    id: "sf-food-cold-storage",
    what: "Cold storage temperature log digitization",
    jurisdiction: "San Francisco",
    eta: "2024-07-01",
    probability: 0.8,
    impact: "Requires hourly logging with automated alerts for any unit above 41°F.",
    source: "eli://sf/ordinances/2024/cold-storage"
  },
  {
    id: "ca-water-audit",
    what: "State water audit attestation",
    jurisdiction: "California",
    eta: "2024-09-15",
    probability: 0.65,
    impact: "Annual submission detailing usage and conservation plan for short-term rentals.",
    source: "eli://ca/statute/2024/water-audit"
  }
];

const PASSPORT_ITEMS: CompliancePassportItem[] = [
  {
    label: "Business registration",
    scope: "San Francisco",
    note: "Filed · Expires Jan 2025"
  },
  {
    label: "Short-term rental license",
    scope: "Office of Short-Term Rentals",
    note: "Valid · Renewal due Nov 2024"
  },
  {
    label: "Food service health permit",
    scope: "San Francisco DPH",
    note: "Inspected Feb 2024"
  }
];

export default function ComplianceHubPage() {
  const horizonClear = HORIZON_ITEMS.length === 0;

  return (
    <div className="bg-[color:var(--ink-0)] text-[color:var(--ink-8)]">
      <SignalBar state={horizonClear ? "clear" : "warning"}>
        {horizonClear
          ? "Status: Compliant. Horizon is clear."
          : `Status: Warning. ${HORIZON_ITEMS.length} changes on the horizon. View action plan.`}
      </SignalBar>
      <PageGrid>
        <Section className="col-span-12 mt-[calc(var(--baseline)*3)]">
          <H1>My Compliance Hub</H1>
          <Body>The present state and the foreseeable future of your obligations.</Body>
          <nav className="flex gap-[calc(var(--baseline)*2)] text-[0.95rem] font-sans mt-[calc(var(--baseline)*2)]">
            <a href="#today" className="font-bold text-[color:var(--ink-9)]">
              Today
            </a>
            <a
              href="#horizon"
              className="font-normal text-[color:var(--ink-6)] hover:text-[color:var(--ink-9)] transition-colors duration-[var(--t-fast)] ease-[var(--ease)]"
            >
              Horizon
            </a>
          </nav>
        </Section>

        <Section className="col-span-12 grid grid-cols-12 gap-x-[calc(var(--baseline)*2)] gap-y-[calc(var(--baseline)*3)]">
          <div className="col-span-12 lg:col-span-8" id="today">
            <H2>Today</H2>
            <Divider />
            <TodayList items={TODAY_ITEMS} />
          </div>
          <aside className="col-span-12 lg:col-span-4" aria-label="Compliance passport">
            <CompliancePassport items={PASSPORT_ITEMS} horizonClear={horizonClear} horizonHref="#horizon" />
          </aside>
          <div className="col-span-12" id="horizon">
            <H2>Horizon</H2>
            <Divider />
            <HorizonTimeline items={HORIZON_ITEMS} />
          </div>
        </Section>
      </PageGrid>
    </div>
  );
}
