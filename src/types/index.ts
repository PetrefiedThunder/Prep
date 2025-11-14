export interface Kitchen {
  id: string;
  name: string;
  hostId: string;
  address: string;
  certificationLevel: string;
  pricing: {
    hourly: number;
    daily?: number;
    weekly?: number;
  };
  equipment: string[];
  availability: AvailabilityWindow[];
}

export interface AvailabilityWindow {
  id: string;
  kitchenId: string;
  startTime: Date;
  endTime: Date;
  recurrenceRule?: string;
  status: "active" | "paused" | "archived";
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "host" | "renter";
  verified: boolean;
  createdAt: Date;
}

export interface Booking {
  id: string;
  userId: string;
  kitchenId: string;
  startTime: Date;
  endTime: Date;
  status: "pending" | "confirmed" | "cancelled" | "completed";
  paymentIntentId?: string;
}
