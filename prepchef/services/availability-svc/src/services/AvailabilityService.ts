import type { PrismaClient, AvailabilityWindow as PrismaAvailabilityWindow } from '@prisma/client';
import { log } from '@prep/logger';

export interface AvailabilityWindow {
  id: string;
  listingId: string;
  dayOfWeek: number | null;
  startTime: Date;
  endTime: Date;
  startDate: Date | null;
  endDate: Date | null;
  isRecurring: boolean;
  createdAt: Date;
}

export interface CreateAvailabilityWindowParams {
  listingId: string;
  dayOfWeek?: number;
  startTime: string; // HH:MM format
  endTime: string; // HH:MM format
  startDate?: Date;
  endDate?: Date;
  isRecurring?: boolean;
}

export interface AvailableSlot {
  start: Date;
  end: Date;
}

/**
 * AvailabilityService handles availability window management
 */
export class AvailabilityService {
  constructor(private prisma: PrismaClient) {}

  /**
   * Get all availability windows for a listing
   */
  async getAvailabilityWindows(listingId: string): Promise<AvailabilityWindow[]> {
    const windows = await this.prisma.availabilityWindow.findMany({
      where: { listingId },
      orderBy: [
        { dayOfWeek: 'asc' },
        { startTime: 'asc' }
      ]
    });

    return windows.map(w => this.mapPrismaWindow(w));
  }

  /**
   * Create a new availability window
   */
  async createAvailabilityWindow(params: CreateAvailabilityWindowParams): Promise<AvailabilityWindow> {
    // Verify listing exists
    const listing = await this.prisma.kitchenListing.findUnique({
      where: { id: params.listingId }
    });

    if (!listing) {
      throw new Error('Listing not found');
    }

    // Parse time strings to Date objects (time component only)
    const startTime = this.parseTime(params.startTime);
    const endTime = this.parseTime(params.endTime);

    const window = await this.prisma.availabilityWindow.create({
      data: {
        listingId: params.listingId,
        dayOfWeek: params.dayOfWeek,
        startTime,
        endTime,
        startDate: params.startDate,
        endDate: params.endDate,
        isRecurring: params.isRecurring ?? true
      }
    });

    log.info('Availability window created', {
      windowId: window.id,
      listingId: params.listingId
    });

    return this.mapPrismaWindow(window);
  }

  /**
   * Delete an availability window
   */
  async deleteAvailabilityWindow(id: string): Promise<void> {
    await this.prisma.availabilityWindow.delete({
      where: { id }
    });

    log.info('Availability window deleted', { windowId: id });
  }

  /**
   * Get available time slots for a listing within a date range
   * This considers availability windows and existing bookings
   */
  async getAvailableSlots(
    listingId: string,
    startDate: Date,
    endDate: Date
  ): Promise<AvailableSlot[]> {
    // Get all availability windows for this listing
    const windows = await this.prisma.availabilityWindow.findMany({
      where: { listingId }
    });

    if (windows.length === 0) {
      return [];
    }

    // Get all confirmed bookings for this listing in the date range
    const bookings = await this.prisma.booking.findMany({
      where: {
        listingId,
        status: {
          notIn: ['canceled', 'no_show']
        },
        startTime: {
          lt: endDate
        },
        endTime: {
          gt: startDate
        }
      },
      select: {
        startTime: true,
        endTime: true
      }
    });

    // Generate available slots based on windows
    const availableSlots: AvailableSlot[] = [];

    // Iterate through each day in the range
    const currentDate = new Date(startDate);
    currentDate.setHours(0, 0, 0, 0);

    while (currentDate <= endDate) {
      const dayOfWeek = currentDate.getDay(); // 0 = Sunday, 6 = Saturday

      // Find matching availability windows for this day
      for (const window of windows) {
        // Check if window applies to this day
        const windowApplies =
          (window.isRecurring && window.dayOfWeek === dayOfWeek) ||
          (!window.isRecurring &&
            window.startDate &&
            window.endDate &&
            currentDate >= window.startDate &&
            currentDate <= window.endDate);

        if (windowApplies) {
          // Create a slot for this window on this day
          const slotStart = new Date(currentDate);
          const windowStartTime = new Date(window.startTime);
          slotStart.setHours(
            windowStartTime.getUTCHours(),
            windowStartTime.getUTCMinutes(),
            0,
            0
          );

          const slotEnd = new Date(currentDate);
          const windowEndTime = new Date(window.endTime);
          slotEnd.setHours(
            windowEndTime.getUTCHours(),
            windowEndTime.getUTCMinutes(),
            0,
            0
          );

          // Check if this slot conflicts with any bookings
          const hasConflict = bookings.some(
            booking =>
              (slotStart >= booking.startTime && slotStart < booking.endTime) ||
              (slotEnd > booking.startTime && slotEnd <= booking.endTime) ||
              (slotStart <= booking.startTime && slotEnd >= booking.endTime)
          );

          if (!hasConflict && slotStart >= startDate && slotEnd <= endDate) {
            availableSlots.push({
              start: slotStart,
              end: slotEnd
            });
          }
        }
      }

      // Move to next day
      currentDate.setDate(currentDate.getDate() + 1);
    }

    return availableSlots;
  }

  /**
   * Parse time string (HH:MM) to Date object
   */
  private parseTime(timeStr: string): Date {
    const [hours, minutes] = timeStr.split(':').map(Number);
    const date = new Date();
    date.setUTCHours(hours, minutes, 0, 0);
    return date;
  }

  /**
   * Map Prisma availability window to response format
   */
  private mapPrismaWindow(window: PrismaAvailabilityWindow): AvailabilityWindow {
    return {
      id: window.id,
      listingId: window.listingId,
      dayOfWeek: window.dayOfWeek,
      startTime: window.startTime,
      endTime: window.endTime,
      startDate: window.startDate,
      endDate: window.endDate,
      isRecurring: window.isRecurring,
      createdAt: window.createdAt
    };
  }
}
