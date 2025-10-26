import type {
  HostListingSummary,
  Listing,
  MessageThread,
  Review,
  Trip,
  Wishlist
} from "./types";

export const listings: Listing[] = [
  {
    id: "hh-seaside-loft",
    slug: "seaside-loft-harborhomes",
    title: "Seaside Loft with Harbor Views",
    heroTagline: "Wake up to the tide in a calming coastal loft",
    description:
      "Experience HarborHomes hospitality in this airy loft perched above the marina. Floor-to-ceiling windows, curated coastal decor, and a chef-ready kitchen make it perfect for short retreats.",
    city: "Monterey",
    country: "United States",
    coordinates: { latitude: 36.6002, longitude: -121.8947 },
    nightlyPrice: 280,
    rating: 4.92,
    reviewCount: 128,
    beds: 2,
    baths: 2,
    guests: 4,
    propertyType: "Loft",
    amenities: [
      "Wi-Fi",
      "Harbor balcony",
      "Chef's kitchen",
      "EV charger",
      "Workspace",
      "Self check-in"
    ],
    images: [
      "https://images.unsplash.com/photo-1505691723518-36a5ac3be353",
      "https://images.unsplash.com/photo-1505691938895-1758d7feb511",
      "https://images.unsplash.com/photo-1505691938895-1758d7feb512",
      "https://images.unsplash.com/photo-1505691938895-1758d7feb513"
    ],
    host: {
      id: "host-aria",
      name: "Aria Chen",
      avatar: "https://images.unsplash.com/photo-1544723795-3fb6469f5b39",
      isSuperhost: true
    },
    highlights: ["Ocean breeze patio", "Curated art", "Dedicated workspace"],
    policies: {
      cancellation: "Full refund up to 7 days before arrival.",
      houseRules: ["No smoking", "No parties", "Quiet hours after 10pm"]
    },
    neighborhood:
      "Located steps from the historic cannery, guests can stroll to indie cafes, art galleries, and kayak rentals. HarborHomes local partners offer exclusive sailing excursions.",
    featured: true
  },
  {
    id: "hh-alpine-retreat",
    slug: "alpine-retreat-harborhomes",
    title: "Alpine Retreat with Cedar Sauna",
    heroTagline: "Warm up after the slopes in a cedar sauna",
    description:
      "A mountain-modern chalet framed by evergreens and large picture windows. Designed for restorative getaways with radiant floors, a private sauna, and outdoor fire lounge.",
    city: "Truckee",
    country: "United States",
    coordinates: { latitude: 39.3279, longitude: -120.1833 },
    nightlyPrice: 410,
    rating: 4.88,
    reviewCount: 96,
    beds: 4,
    baths: 3,
    guests: 8,
    propertyType: "Chalet",
    amenities: [
      "Sauna",
      "Hot tub",
      "Ski-in access",
      "EV charger",
      "Washer",
      "Pet friendly"
    ],
    images: [
      "https://images.unsplash.com/photo-1505691938895-1758d7feb509",
      "https://images.unsplash.com/photo-1505691938895-1758d7feb510",
      "https://images.unsplash.com/photo-1493666438817-866a91353ca9"
    ],
    host: {
      id: "host-luca",
      name: "Luca Marin",
      avatar: "https://images.unsplash.com/photo-1521572267360-ee0c2909d518",
      isSuperhost: true
    },
    highlights: ["Gear drying room", "Panoramic deck", "Trail maps included"],
    policies: {
      cancellation: "Full refund up to 14 days before arrival.",
      houseRules: ["Pets welcome", "No smoking", "Respect snow removal signage"]
    },
    neighborhood:
      "Nestled near Donner Lake, minutes from alpine ski resorts and local bakeries. HarborHomes concierge can arrange lift tickets and gear delivery.",
    featured: true
  },
  {
    id: "hh-city-haven",
    slug: "city-haven-harborhomes",
    title: "City Haven with Rooftop Lounge",
    heroTagline: "Urban energy, HarborHomes ease",
    description:
      "A design-forward apartment in the heart of the arts district with curated furnishings, a record nook, and private rooftop lounge with skyline views.",
    city: "Austin",
    country: "United States",
    coordinates: { latitude: 30.2672, longitude: -97.7431 },
    nightlyPrice: 210,
    rating: 4.7,
    reviewCount: 54,
    beds: 1,
    baths: 1,
    guests: 2,
    propertyType: "Apartment",
    amenities: [
      "Rooftop lounge",
      "Gym",
      "Fast Wi-Fi",
      "Self check-in",
      "Pet friendly",
      "EV charger"
    ],
    images: [
      "https://images.unsplash.com/photo-1505691938895-1758d7feb520",
      "https://images.unsplash.com/photo-1489171078254-c3365d6e359f",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267"
    ],
    host: {
      id: "host-sloane",
      name: "Sloane Patel",
      avatar: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1",
      isSuperhost: false
    },
    highlights: ["In-unit espresso", "Rooftop loungers", "Smart home controls"],
    policies: {
      cancellation: "Full refund within 5 days of arrival.",
      houseRules: ["No smoking", "Parties not permitted"]
    },
    neighborhood:
      "Walkable to live music, boutique coffee, and the riverfront trail. HarborHomes partners include local studios for drop-in wellness sessions.",
    featured: false
  }
];

export const reviews: Review[] = [
  {
    id: "rev-001",
    listingId: "hh-seaside-loft",
    author: {
      name: "Jordan",
      avatar: "https://images.unsplash.com/photo-1544723795-3fb6469f5b39",
      trips: 4
    },
    createdAt: "2024-01-15",
    cleanliness: 5,
    accuracy: 5,
    communication: 5,
    location: 5,
    value: 4,
    text: "Loved waking up to the marina views. The HarborHomes team checked in with local recommendations and a fresh pastry delivery."
  },
  {
    id: "rev-002",
    listingId: "hh-alpine-retreat",
    author: {
      name: "Priya",
      avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2",
      trips: 6
    },
    createdAt: "2024-02-20",
    cleanliness: 5,
    accuracy: 4,
    communication: 5,
    location: 5,
    value: 5,
    text: "Perfect après-ski sanctuary. Sauna was spotless and the guidebook listed hidden snowshoe trails."
  }
];

export const wishlists: Wishlist[] = [
  {
    id: "wl-dream-coast",
    name: "Dreamy Coasts",
    isPrivate: false,
    listingIds: ["hh-seaside-loft"]
  }
];

export const messageThreads: MessageThread[] = [
  {
    id: "msg-aria",
    listingId: "hh-seaside-loft",
    participant: {
      id: "host-aria",
      name: "Aria Chen",
      avatar: "https://images.unsplash.com/photo-1544723795-3fb6469f5b39"
    },
    lastMessagePreview: "We'd love to welcome you back in June!",
    lastMessageAt: "2024-03-05T09:15:00Z",
    unread: true,
    messages: [
      {
        id: "msg-aria-1",
        senderId: "host-aria",
        body: "Hi! Let me know if you'd like recommendations for sailing charters.",
        sentAt: "2024-02-12T17:02:00Z"
      },
      {
        id: "msg-aria-2",
        senderId: "guest-me",
        body: "Thanks Aria! We booked the sunset sail you suggested.",
        sentAt: "2024-02-12T19:10:00Z"
      }
    ]
  }
];

export const trips: Trip[] = [
  {
    id: "trip-001",
    listingId: "hh-seaside-loft",
    startDate: "2024-05-10",
    endDate: "2024-05-15",
    guests: 2,
    total: 1450
  }
];

export const hostListings: HostListingSummary[] = [
  {
    id: "hh-seaside-loft",
    title: "Seaside Loft with Harbor Views",
    status: "published",
    views: 1280,
    bookings: 42,
    revenue: 25700
  },
  {
    id: "hh-alpine-retreat",
    title: "Alpine Retreat with Cedar Sauna",
    status: "draft",
    views: 760,
    bookings: 18,
    revenue: 16400
  }
];
