export type Anomaly = {
  type: string;
  details: Record<string, unknown>;
};

type GeneratedSpec = {
  summary: string;
  changes: Array<{ file: string; type: string }>;
  tests: Array<{ file: string; kind: string }>;
  constraints: string[];
};

export function synthSpec(anomaly: Anomaly): GeneratedSpec | undefined {
  if (anomaly.type === "toast_recon_variance") {
    return {
      summary: "Fix Toast mapper idempotency",
      changes: [{ file: "/apps/data-plane/mappers/toast.ts", type: "adapter" }],
      tests: [
        { file: "/apps/data-plane/tests/toast.spec.ts", kind: "unit" },
        { file: "/apps/data-plane/tests/pact/toast.pact.ts", kind: "contract" },
      ],
      constraints: ["no_core_auth_payment_changes"],
    };
  }
  return undefined;
}
