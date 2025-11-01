interface SummaryCardProps {
  label: string;
  value: string;
  helper?: string;
}

export function SummaryCard({ label, value, helper }: SummaryCardProps) {
  return (
    <div className="summary-card">
      <h3>{label}</h3>
      <strong>{value}</strong>
      {helper ? <span>{helper}</span> : null}
    </div>
  );
}
