'use client';

import { DayPicker, type DayPickerRangeProps } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import { cn } from '@/lib/utils';

export type CalendarProps = DayPickerRangeProps;

export const Calendar = ({ className, ...props }: CalendarProps) => (
  <DayPicker
    className={cn('flex justify-center', className)}
    classNames={{
      caption_label: 'text-sm font-medium',
      months: 'flex flex-col gap-4 md:flex-row',
      nav_button: 'rounded-full p-2 text-muted-ink hover:bg-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-brand',
      day: 'h-10 w-10 rounded-full text-sm aria-selected:bg-brand aria-selected:text-brand-contrast focus:outline-none focus-visible:ring-2 focus-visible:ring-brand',
      table: 'w-full border-collapse space-y-1'
    }}
    {...props}
  />
);
