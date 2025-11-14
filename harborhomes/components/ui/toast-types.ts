import type { ReactNode } from "react";

export type ToastProps = {
  id: string;
  title?: string;
  description?: string;
  action?: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};
