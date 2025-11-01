import { render, screen } from "@testing-library/react";
import type { MockedFunction } from "vitest";

import SfAndJtPage from "@/app/sf-and-jt/page";
import { fetchCityCompliance, type CityCompliance } from "@/lib/compliance";

vi.mock("@/lib/compliance", () => ({
  fetchCityCompliance: vi.fn()
}));

const mockFetchCityCompliance = fetchCityCompliance as MockedFunction<typeof fetchCityCompliance>;

function buildCompliance(overrides: Partial<CityCompliance>): CityCompliance {
  return {
    jurisdiction: "test",
    paperwork: ["Primary application"],
    fees: [
      {
        name: "Application fee",
        amount_cents: 12000,
        kind: "one_time"
      }
    ],
    totals: {
      one_time_cents: 12000,
      recurring_annualized_cents: 0,
      incremental_fee_count: 0
    },
    validation: {
      is_valid: true,
      issues: []
    },
    ...overrides
  };
}

describe("SfAndJtPage", () => {
  beforeEach(() => {
    mockFetchCityCompliance.mockReset();
  });

  it("renders compliance data for both cities", async () => {
    mockFetchCityCompliance.mockResolvedValueOnce(
      buildCompliance({
        jurisdiction: "san_francisco",
        paperwork: ["Food permit application", "Fire inspection clearance"],
        fees: [
          { name: "Annual Health Permit", amount_cents: 98000, kind: "recurring", cadence: "annual" },
          { name: "Plan Review", amount_cents: 45000, kind: "one_time" }
        ]
      })
    );
    mockFetchCityCompliance.mockResolvedValueOnce(
      buildCompliance({
        jurisdiction: "joshua_tree",
        paperwork: ["County field inspection", "Water safety certification"],
        fees: [
          { name: "San Bernardino County Permit", amount_cents: 76000, kind: "recurring", cadence: "annual" }
        ],
        totals: {
          one_time_cents: 0,
          recurring_annualized_cents: 76000,
          incremental_fee_count: 1
        }
      })
    );

    const Page = await SfAndJtPage();
    render(Page);

    expect(mockFetchCityCompliance).toHaveBeenNthCalledWith(1, "san-francisco");
    expect(mockFetchCityCompliance).toHaveBeenNthCalledWith(2, "joshua-tree");
    expect(screen.getByRole("heading", { name: "San Francisco, CA" })).toBeInTheDocument();
    expect(screen.getByText("Annual Health Permit")).toBeInTheDocument();
    expect(screen.getByText("San Bernardino County Permit")).toBeInTheDocument();
    expect(screen.getAllByText(/Permit active/i)).toHaveLength(2);
  });

  it("surfaces guidance when the compliance API is unavailable", async () => {
    mockFetchCityCompliance.mockResolvedValueOnce(
      buildCompliance({ jurisdiction: "san_francisco", paperwork: ["Food permit application"] })
    );
    mockFetchCityCompliance.mockRejectedValueOnce(new Error("NEXT_PUBLIC_API_BASE is not configured"));

    const Page = await SfAndJtPage();
    render(Page);

    expect(screen.getByRole("heading", { name: "Joshua Tree, CA" })).toBeInTheDocument();
    expect(screen.getByText(/Unable to load compliance data/)).toBeInTheDocument();
    expect(
      screen.getByText(/Set NEXT_PUBLIC_API_BASE to the base URL of your compliance API to stream live data/)
    ).toBeInTheDocument();
  });
});
