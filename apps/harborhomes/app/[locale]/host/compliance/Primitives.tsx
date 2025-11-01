import * as React from "react";
import clsx from "clsx";

export function PageGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-6xl px-[var(--baseline)] lg:px-[calc(var(--baseline)*3)]">
      <div className="grid grid-cols-12 gap-x-[calc(var(--baseline)*2)] gap-y-[calc(var(--baseline)*3)]">
        {children}
      </div>
    </div>
  );
}

export function Section({ children, className }: { children: React.ReactNode; className?: string }) {
  return <section className={clsx("col-span-12", className)}>{children}</section>;
}

export function H1({ children }: { children: React.ReactNode }) {
  return (
    <h1 className="font-sans font-light text-[2.236rem] leading-[1.1] tracking-[-0.01em] text-[color:var(--ink-9)]">
      {children}
    </h1>
  );
}

export function H2({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mt-[calc(var(--baseline)*1)] font-sans text-[1.414rem] leading-[1.2] font-medium text-[color:var(--ink-9)]">
      {children}
    </h2>
  );
}

export function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-sans text-[1rem] leading-[1.5] text-[color:var(--ink-8)] max-w-prose">
      {children}
    </p>
  );
}

type Signal = "clear" | "warning" | "error";
export function SignalBar({ state, children }: { state: Signal; children: React.ReactNode }) {
  const color =
    state === "clear"
      ? "bg-[color:var(--signal-green)]"
      : state === "warning"
      ? "bg-[color:var(--signal-amber)]"
      : "bg-[color:var(--signal-red)]";
  return (
    <div role="status" aria-live="polite" className={clsx("w-full", color)}>
      <div className="mx-auto max-w-6xl px-[calc(var(--baseline)*2)] py-[calc(var(--baseline)*1.5)] text-[0.875rem] font-sans font-medium text-white">
        {children}
      </div>
    </div>
  );
}

export function Divider() {
  return <hr className="my-[calc(var(--baseline)*2)] border-0 h-px bg-[color:var(--ink-2)]" />;
}

export function HairlineDot({ colorVar = "--signal-amber" }: { colorVar?: string }) {
  return (
    <span
      aria-hidden
      className="absolute -left-[9px] mt-[6px] inline-block h-2 w-2 rounded-full"
      style={{ backgroundColor: `var(${colorVar})` }}
    />
  );
}
