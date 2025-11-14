import { differenceInCalendarDays, format, parseISO } from "date-fns";

export function formatDateRange(start: string, end: string) {
  return `${format(parseISO(start), "MMM d")} – ${format(parseISO(end), "MMM d, yyyy")}`;
}

export function calculateNights(start: string, end: string) {
  return Math.max(differenceInCalendarDays(parseISO(end), parseISO(start)), 1);
}
