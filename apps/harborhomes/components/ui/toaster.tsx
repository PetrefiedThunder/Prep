'use client';

import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport
} from '@radix-ui/react-toast';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export const Toaster = () => (
  <ToastProvider swipeDirection="right">
    <ToastViewport className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-3" />
  </ToastProvider>
);

export const AppToast = ({ title, description }: { title: string; description?: string }) => (
  <Toast className="relative w-full rounded-2xl border border-border bg-white p-4 shadow-lg">
    <div className="flex flex-col gap-2">
      <ToastTitle className="text-sm font-semibold text-ink">{title}</ToastTitle>
      {description ? <ToastDescription className="text-sm text-muted-ink">{description}</ToastDescription> : null}
    </div>
    <ToastClose className={cn('absolute right-3 top-3 rounded-full bg-surface p-1 text-muted-ink focus:outline-none')}>
      <X className="h-4 w-4" />
    </ToastClose>
  </Toast>
);
