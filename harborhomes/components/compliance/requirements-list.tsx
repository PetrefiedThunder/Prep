interface RequirementsListProps {
  items: string[];
  title?: string;
}

export function RequirementsList({ items, title = "Required paperwork" }: RequirementsListProps) {
  return (
    <section className="rounded-2xl border border-dashed border-border bg-surface p-5">
      <p className="text-sm font-semibold uppercase tracking-wide text-muted-ink">{title}</p>
      <ul className="mt-3 space-y-2 text-sm text-ink">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-brand" aria-hidden />
            <span className="leading-relaxed text-muted-ink">{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
