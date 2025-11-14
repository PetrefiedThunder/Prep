import { render, screen } from "@testing-library/react";
import { FeeCard } from "@/components/prep/FeeCard";
import { RequirementsList } from "@/components/prep/RequirementsList";
import { PermitBadge } from "@/components/prep/PermitBadge";
import type { CityCompliance, Fee } from "@/lib/compliance";

describe("Compliance components", () => {
  const fee: Fee = {
    name: "Annual Health Permit",
    amount_cents: 98000,
    kind: "recurring",
    cadence: "annual"
  };

  const compliance: CityCompliance = {
    jurisdiction: "san_francisco",
    paperwork: ["Application Form A-FOOD", "Plan Review Checklist PRC-12"],
    fees: [fee],
    totals: {
      one_time_cents: 45000,
      recurring_annualized_cents: 98000,
      incremental_fee_count: 1
    },
    validation: {
      is_valid: true,
      issues: []
    }
  };

  it("renders fee amount in dollars", () => {
    render(<FeeCard fee={fee} />);
    expect(screen.getByText("$980")).toBeInTheDocument();
  });

  it("lists paperwork requirements", () => {
    render(<RequirementsList items={compliance.paperwork} />);
    expect(screen.getByText(compliance.paperwork[0])).toBeInTheDocument();
    expect(screen.getByText(compliance.paperwork[1])).toBeInTheDocument();
  });

  it("highlights permit status", () => {
    render(<PermitBadge validation={compliance.validation} totals={compliance.totals} />);
    expect(screen.getByText(/Ready/i)).toBeInTheDocument();
    expect(screen.getByText(/One-time fees/)).toBeInTheDocument();
  });
});
