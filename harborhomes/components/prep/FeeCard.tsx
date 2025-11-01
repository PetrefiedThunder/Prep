import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/currency";
import type { CityCompliance } from "@/lib/compliance";
import { cn } from "@/lib/utils";

type Fee = CityCompliance["fees"][number];

const KIND_LABEL: Record<Fee["kind"], string> = {
  one_time: "One-time",
  recurring: "Recurring",
  incremental: "Incremental"
};

const titleize = (value: string) => value.replace(/_/g, " ").replace(/\b([a-z])/g, (match) => match.toUpperCase());

function formatDescriptor(fee: Fee) {
  const parts = [KIND_LABEL[fee.kind] ?? "Fee"];
  if (fee.cadence) {
    parts.push(titleize(fee.cadence));
  } else if (fee.unit) {
    parts.push(titleize(fee.unit));
  }
  return parts.join(" · ");
}

export interface FeeCardProps {
  fee: Fee;
  highlight?: boolean;
}

export function FeeCard({ fee, highlight = false }: FeeCardProps) {
  const amount = formatCurrency(fee.amount_cents / 100);
  const descriptor = formatDescriptor(fee);

  return (
    <article
      className={cn(
        "rounded-2xl border border-border bg-white p-5 shadow-sm transition hover:shadow-md",
        highlight && "border-brand/70 shadow-md"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-ink">{descriptor}</p>
          <h3 className="mt-1 text-lg font-semibold text-ink">{fee.name}</h3>
        </div>
        <Badge variant="brand" className="whitespace-nowrap text-sm">
          {amount}
        </Badge>
      </div>
      {fee.kind === "recurring" ? (
        <p className="mt-3 text-sm text-muted-ink">Renewed on a {fee.cadence ? titleize(fee.cadence) : "recurring"} basis.</p>
      ) : fee.kind === "incremental" ? (
        <p className="mt-3 text-sm text-muted-ink">
          Applied {fee.unit ? titleize(fee.unit) : "as needed"} when follow-up inspections are required.
        </p>
      ) : (
        <p className="mt-3 text-sm text-muted-ink">Charged once upon submission approval.</p>
      )}
    </article>
  );
}
