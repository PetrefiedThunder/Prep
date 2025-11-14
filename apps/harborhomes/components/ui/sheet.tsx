'use client';

import * as SheetPrimitive from '@radix-ui/react-dialog';
import { cn } from '@/lib/utils';
import { forwardRef } from 'react';

export const Sheet = SheetPrimitive.Root;
export const SheetTrigger = SheetPrimitive.Trigger;
export const SheetClose = SheetPrimitive.Close;

export const SheetContent = forwardRef<HTMLDivElement, SheetPrimitive.DialogContentProps>(
  ({ className, side = 'right', children, ...props }, ref) => (
    <SheetPrimitive.Portal>
      <SheetPrimitive.Overlay className="fixed inset-0 z-40 bg-black/40" />
      <SheetPrimitive.Content
        ref={ref}
        className={cn(
          'fixed inset-y-0 z-50 flex w-full max-w-md flex-col gap-6 bg-white p-6 shadow-xl transition data-[state=closed]:animate-slide-out data-[state=open]:animate-slide-in dark:bg-surface',
          side === 'left' ? 'left-0' : 'right-0',
          className
        )}
        {...props}
      >
        {children}
      </SheetPrimitive.Content>
    </SheetPrimitive.Portal>
  )
);

SheetContent.displayName = SheetPrimitive.Content.displayName;
