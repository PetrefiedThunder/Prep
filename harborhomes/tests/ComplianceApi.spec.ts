import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchCityCompliance, type CityCompliance } from "@/lib/compliance";

describe("fetchCityCompliance", () => {
  const originalBase = process.env.COMPLIANCE_API_BASE;
  const originalKey = process.env.COMPLIANCE_API_KEY;

  beforeEach(() => {
    process.env.COMPLIANCE_API_BASE = "https://api.test";
    process.env.COMPLIANCE_API_KEY = "secret";
  });

  afterEach(() => {
    process.env.COMPLIANCE_API_BASE = originalBase;
    process.env.COMPLIANCE_API_KEY = originalKey;
    vi.restoreAllMocks();
  });

  it("requests the city endpoint", async () => {
    const response: CityCompliance = {
      jurisdiction: "san_francisco",
      paperwork: [],
      fees: [],
      totals: {
        one_time_cents: 0,
        recurring_annualized_cents: 0,
        incremental_fee_count: 0
      },
      validation: {
        is_valid: true,
        issues: []
      }
    };

    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => response
    } as Response);

    const payload = await fetchCityCompliance("san-francisco");

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://api.test/city/san-francisco/fees",
      expect.objectContaining({
        headers: expect.objectContaining({
          Accept: "application/json",
          "x-api-key": "secret"
        })
      })
    );
    expect(payload).toEqual(response);
  });

  it("throws when the API base is missing", async () => {
    delete process.env.COMPLIANCE_API_BASE;
    delete process.env.NEXT_PUBLIC_API_BASE;
    await expect(fetchCityCompliance("san-francisco")).rejects.toThrow(/COMPLIANCE_API_BASE/);
  });
});
