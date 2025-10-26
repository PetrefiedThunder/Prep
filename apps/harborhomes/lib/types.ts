export type Amenity =
  | 'wifi'
  | 'workspace'
  | 'kitchen'
  | 'parking'
  | 'pet-friendly'
  | 'ev-charger'
  | 'pool'
  | 'hot-tub'
  | 'washer'
  | 'dryer'
  | 'air-conditioning';

export interface Listing {
  id: string;
  title: string;
  description: string;
  city: string;
  country: string;
  coordinates: [number, number];
  pricePerNight: number;
  rating: number;
  reviewCount: number;
  beds: number;
  baths: number;
  guests: number;
  photos: string[];
  amenities: Amenity[];
  hostId: string;
  hostName: string;
  tags: string[];
  featured?: boolean;
  category: string;
}

export interface Review {
  id: string;
  listingId: string;
  author: string;
  avatar: string;
  rating: number;
  createdAt: string;
  body: string;
  scores: {
    cleanliness: number;
    accuracy: number;
    communication: number;
    location: number;
    checkIn: number;
    value: number;
  };
}

export interface Wishlist {
  id: string;
  name: string;
  isPrivate: boolean;
  coverPhoto?: string;
  listingIds: string[];
}

export interface MessageThread {
  id: string;
  listingId: string;
  participants: string[];
  lastMessageAt: string;
  unreadCount: number;
  messages: Array<{
    id: string;
    author: string;
    body: string;
    createdAt: string;
  }>;
}

export interface Trip {
  id: string;
  listingId: string;
  startDate: string;
  endDate: string;
  status: 'upcoming' | 'completed' | 'cancelled';
}

export interface CheckoutPayload {
  listingId: string;
  startDate: string;
  endDate: string;
  guests: number;
  fullName: string;
  email: string;
  phone: string;
}

export interface AnalyticsEvent {
  name: 'search' | 'filter_apply' | 'listing_view' | 'start_checkout' | 'save_wishlist';
  properties?: Record<string, string | number | boolean>;
}
