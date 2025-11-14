import { differenceInCalendarDays, format, parseISO } from 'date-fns';

export const formatRange = (start?: string, end?: string) => {
  if (!start || !end) return 'Any week';
  return `${format(parseISO(start), 'MMM d')} – ${format(parseISO(end), 'MMM d')}`;
};

export const nightsBetween = (start: string, end: string) =>
  Math.max(1, differenceInCalendarDays(parseISO(end), parseISO(start)));
