"use client";

import "../../../styles/compliance.theme.css";

import * as React from "react";
import { useSearchParams } from "next/navigation";

export default function SourceViewer() {
  const params = useSearchParams();
  const eli = params.get("eli") || "";
  const [sections, setSections] = React.useState<string[]>([]);

  React.useEffect(() => {
    if (!eli) return;
    (async () => {
      const r = await fetch(`/api/source?eli=${encodeURIComponent(eli)}`, { cache: "no-store" });
      const data = await r.json();
      setSections(data.sections || []);
    })();
  }, [eli]);

  return (
    <main className="mx-auto max-w-3xl px-[calc(var(--baseline)*2)] py-[calc(var(--baseline)*3)]">
      <h1 className="font-sans font-light text-[2.236rem] leading-[1.1] tracking-[-0.01em] text-[color:var(--ink-9)]">
        {eli || "Document"}
      </h1>
      <div className="mt-[calc(var(--baseline)*2)] space-y-[calc(var(--baseline)*2)]">
        {sections.map((s, i) => (
          <p key={i} className="font-sans text-[1rem] leading-[1.6] text-[color:var(--ink-8)] max-w-prose">
            {s}
          </p>
        ))}
      </div>
    </main>
  );
}
