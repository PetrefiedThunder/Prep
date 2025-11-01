import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/currency";
import type { CityCompliance } from "@/lib/compliance";

type Validation = CityCompliance["validation"];
type Totals = CityCompliance["totals"];

export interface PermitBadgeProps {
  validation: Validation;
  totals: Totals;
}

function formatIssueCopy(validation: Validation) {
  if (validation.is_valid) {
    return "Filings are current";
  }

  const issueCount = validation.issues.length;
  if (issueCount === 0) {
    return "Awaiting compliance review";
  }

  return `${issueCount} outstanding ${issueCount === 1 ? "issue" : "issues"}`;
}

export function PermitBadge({ validation, totals }: PermitBadgeProps) {
  const statusLabel = validation.is_valid ? "Ready" : "Action needed";
  const badgeVariant = validation.is_valid ? "brand" : "outline";

  return (
    <div className="rounded-2xl border border-border bg-white px-4 py-3 shadow-sm">
      <Badge variant={badgeVariant} className="mb-2 text-xs uppercase tracking-wide">
        {statusLabel}
      </Badge>
      <p className="text-sm font-medium text-ink">{formatIssueCopy(validation)}</p>
      <p className="mt-1 text-xs text-muted-ink">
        One-time fees {formatCurrency(totals.one_time_cents / 100)} · Annual renewals{" "}
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
