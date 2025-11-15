"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

type MaintenanceBannerProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function MaintenanceBanner({ title, description, actionLabel, onAction }: MaintenanceBannerProps) {
  return (
    <div className="flex flex-col gap-3 rounded-3xl border border-dashed border-amber-200 bg-amber-50 p-6 text-amber-900">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        <h2 className="text-sm font-semibold uppercase tracking-wide">{title}</h2>
      </div>
      <p className="text-sm text-amber-900/90">{description}</p>
      {actionLabel && onAction ? (
        <div>
          <Button size="sm" variant="outline" className="border-amber-300 text-amber-900 hover:bg-amber-100" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
