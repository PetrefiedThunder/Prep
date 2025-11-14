export type Coordinate = {
  latitude: number;
  longitude: number;
};

export type Listing = {
  id: string;
  title: string;
  slug: string;
  description: string;
  city: string;
  country: string;
  coordinates: Coordinate;
  nightlyPrice: number;
  rating: number;
  reviewCount: number;
  beds: number;
  baths: number;
  guests: number;
  propertyType: string;
  amenities: string[];
  images: string[];
  host: {
    id: string;
    name: string;
    avatar: string;
    isSuperhost: boolean;
  };
  highlights: string[];
  policies: {
    cancellation: string;
    houseRules: string[];
  };
  neighborhood: string;
  heroTagline: string;
  featured: boolean;
};

export type Review = {
  id: string;
  listingId: string;
  author: {
    name: string;
    avatar: string;
    trips: number;
  };
  createdAt: string;
  cleanliness: number;
  accuracy: number;
  communication: number;
  location: number;
  value: number;
  text: string;
};

export type Wishlist = {
  id: string;
  name: string;
  isPrivate: boolean;
  listingIds: string[];
};

export type MessageThread = {
  id: string;
  listingId: string;
  participant: {
    id: string;
    name: string;
    avatar: string;
  };
  lastMessagePreview: string;
  lastMessageAt: string;
  unread: boolean;
  messages: Array<{
    id: string;
    senderId: string;
    body: string;
    sentAt: string;
  }>;
};

export type Trip = {
  id: string;
  listingId: string;
  startDate: string;
  endDate: string;
  guests: number;
  total: number;
};

export type HostListingSummary = {
  id: string;
  title: string;
  status: "draft" | "published";
  views: number;
  bookings: number;
  revenue: number;
};

export type AnalyticsEvent =
  | {
      type: "search";
      query: string;
      guests: number;
      startDate?: string;
      endDate?: string;
    }
  | {
      type: "filter_apply";
      filters: Record<string, unknown>;
    }
  | {
      type: "listing_view";
      listingId: string;
    }
  | {
      type: "start_checkout";
      listingId: string;
      total: number;
    }
  | {
      type: "save_wishlist";
      listingId: string;
      wishlistId: string;
    };
