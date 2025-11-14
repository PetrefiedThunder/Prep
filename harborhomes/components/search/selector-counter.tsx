"use client";

import { Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LabelledCounterProps {
  label: string;
  helper?: string;
  value: number;
  onChange: (value: number) => void;
}

export function LabelledCounter({ label, helper, value, onChange }: LabelledCounterProps) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-border px-4 py-3">
      <div>
        <p className="text-sm font-semibold text-ink">{label}</p>
        {helper && <p className="text-xs text-muted-ink">{helper}</p>}
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="icon"
          variant="ghost"
          onClick={() => onChange(Math.max(0, value - 1))}
          aria-label={`Decrease ${label}`}
        >
          <Minus className="h-4 w-4" />
        </Button>
        <span className="w-6 text-center text-sm font-semibold">{value}</span>
        <Button
          size="icon"
          variant="ghost"
          onClick={() => onChange(value + 1)}
          aria-label={`Increase ${label}`}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
