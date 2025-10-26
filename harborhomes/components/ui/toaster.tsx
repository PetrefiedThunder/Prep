"use client";

import * as ToastPrimitives from "@radix-ui/react-toast";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, X } from "lucide-react";
import { useToast } from "./use-toast";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <ToastPrimitives.Provider swipeDirection="right">
      <div className="pointer-events-none fixed bottom-6 right-6 flex flex-col gap-3">
        <AnimatePresence>
          {toasts.map(({ id, title, description, action, open }) => (
            <ToastPrimitives.Root
              key={id}
              open={open}
              onOpenChange={(next) => {
                if (!next) dismiss(id);
              }}
              forceMount
              className="pointer-events-auto w-80 rounded-2xl border border-border bg-white p-4 shadow-floating focus:outline-none"
            >
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                transition={{ type: "spring", duration: 0.35, bounce: 0 }}
                className="flex items-start gap-3"
              >
                <span className="mt-1 text-brand">
                  <CheckCircle2 className="h-5 w-5" />
                </span>
                <div className="flex-1">
                  {title && <p className="text-sm font-semibold text-ink">{title}</p>}
                  {description && <p className="mt-1 text-sm text-muted-ink">{description}</p>}
                  {action}
                </div>
                <button
                  onClick={() => dismiss(id)}
                  className="rounded-full p-2 text-muted-ink transition hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                >
                  <X className="h-4 w-4" />
                  <span className="sr-only">Dismiss</span>
                </button>
              </motion.div>
            </ToastPrimitives.Root>
          ))}
        </AnimatePresence>
      </div>
    </ToastPrimitives.Provider>
  );
}
