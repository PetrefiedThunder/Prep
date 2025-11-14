import { DayPicker } from "react-day-picker";
import { cn } from "@/lib/utils";
import "react-day-picker/dist/style.css";

export type CalendarProps = React.ComponentProps<typeof DayPicker>;

export function Calendar({ className, classNames, ...props }: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col sm:flex-row gap-6",
        caption: "flex justify-center pt-1 relative items-center text-ink",
        caption_label: "text-sm font-medium",
        nav: "space-x-1 flex items-center",
        nav_button:
          "h-9 w-9 bg-transparent hover:bg-surface text-ink inline-flex items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand",
        table: "w-full border-collapse space-y-1",
        head_row: "flex",
        head_cell: "w-10 font-semibold text-xs text-muted-ink",
        row: "flex w-full mt-2",
        cell: "relative h-10 w-10 text-center text-sm focus-within:relative focus-within:z-20",
        day: "h-10 w-10 rounded-full p-0 font-normal hover:bg-brand/10",
        day_selected: "bg-brand text-brand-contrast hover:bg-brand",
        day_today: "border border-brand text-ink",
        day_outside: "opacity-40",
        day_disabled: "opacity-20",
        range_start: "bg-brand text-brand-contrast",
        range_end: "bg-brand text-brand-contrast"
      }}
      {...props}
    />
  );
}
