import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/currency";
import type { CityCompliance } from "@/lib/compliance";

interface PermitBadgeProps {
  validation: CityCompliance["validation"];
  totals: CityCompliance["totals"];
}

export function PermitBadge({ validation, totals }: PermitBadgeProps) {
  const statusLabel = validation.is_valid ? "Permit active" : "Permit review needed";
  const detail = validation.is_valid
    ? "Filings are current"
    : `${validation.issues.length} outstanding ${validation.issues.length === 1 ? "issue" : "issues"}`;

  return (
    <div className="rounded-2xl border border-border bg-white px-4 py-3 shadow-sm">
      <Badge variant={validation.is_valid ? "brand" : "outline"} className="mb-2 text-xs">
        {statusLabel}
      </Badge>
      <p className="text-sm font-medium text-ink">{detail}</p>
      <p className="mt-1 text-xs text-muted-ink">
        One-time fees {formatCurrency(totals.one_time_cents / 100)} · Annual renewals {" "}
        {formatCurrency(totals.recurring_annualized_cents / 100)}
      </p>
      {totals.incremental_fee_count > 0 && (
        <p className="mt-1 text-xs text-muted-ink">
          {totals.incremental_fee_count} incremental {totals.incremental_fee_count === 1 ? "fee" : "fees"} may apply during follow-up visits.
        </p>
      )}
    </div>
  );
}
