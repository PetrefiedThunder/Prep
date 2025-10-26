import { addDays, formatISO } from 'date-fns';
import type { Listing, MessageThread, Review, Trip, Wishlist } from './types';

export const listings: Listing[] = [
  {
    id: 'harbor-loft',
    title: 'Sunrise Loft over the Harbor',
    description:
      'Wake up to sweeping waterfront views in this airy loft with floor-to-ceiling windows and a chef-ready kitchen.',
    city: 'Seattle',
    country: 'United States',
    coordinates: [-122.3376, 47.6119],
    pricePerNight: 320,
    rating: 4.92,
    reviewCount: 84,
    beds: 2,
    baths: 2,
    guests: 4,
    photos: [
      'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85',
      'https://images.unsplash.com/photo-1493809842364-78817add7ffb',
      'https://images.unsplash.com/photo-1505691723518-36a5ac3be353'
    ],
    amenities: ['wifi', 'workspace', 'kitchen', 'washer', 'dryer', 'air-conditioning', 'ev-charger'],
    hostId: 'host-lena',
    hostName: 'Lena',
    tags: ['Self check-in', 'Waterfront'],
    featured: true,
    category: 'Waterfront'
  },
  {
    id: 'desert-retreat',
    title: 'Starlight Desert Retreat',
    description: 'Minimalist desert pod with panoramic stargazing deck and cooling plunge pool.',
    city: 'Joshua Tree',
    country: 'United States',
    coordinates: [-116.3131, 34.1347],
    pricePerNight: 210,
    rating: 4.88,
    reviewCount: 132,
    beds: 1,
    baths: 1,
    guests: 2,
    photos: [
      'https://images.unsplash.com/photo-1505691938895-1758d7feb511',
      'https://images.unsplash.com/photo-1507089947368-19c1da9775ae',
      'https://images.unsplash.com/photo-1505691938895-1758d7feb511?crop=faces&fit=crop&w=800&h=600'
    ],
    amenities: ['wifi', 'parking', 'pool', 'hot-tub', 'air-conditioning'],
    hostId: 'host-milo',
    hostName: 'Milo',
    tags: ['Eco stay', 'Solar powered'],
    category: 'Design'
  },
  {
    id: 'alpine-chalet',
    title: 'HarborHomes Alpine Chalet',
    description: 'A-frame chalet with cedar sauna, ski-in access, and sweeping alpine meadows.',
    city: 'Aspen',
    country: 'United States',
    coordinates: [-106.837, 39.1911],
    pricePerNight: 640,
    rating: 4.97,
    reviewCount: 46,
    beds: 4,
    baths: 3,
    guests: 8,
    photos: [
      'https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=1200&q=80',
      'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267',
      'https://images.unsplash.com/photo-1505691723518-36a5ac3be353?auto=format&fit=crop&w=1200&q=80'
    ],
    amenities: ['wifi', 'kitchen', 'parking', 'hot-tub', 'washer', 'dryer'],
    hostId: 'host-ari',
    hostName: 'Ari',
    tags: ['Snowfront', 'Sauna'],
    category: 'Cabins'
  }
];

export const reviews: Review[] = [
  {
    id: 'review-1',
    listingId: 'harbor-loft',
    author: 'Chloe',
    avatar: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1',
    rating: 5,
    createdAt: formatISO(addDays(new Date(), -12)),
    body: 'The views are extraordinary and the kitchen had everything we needed. HarborHomes made our stay seamless.',
    scores: {
      cleanliness: 5,
      accuracy: 5,
      communication: 5,
      location: 5,
      checkIn: 5,
      value: 4
    }
  },
  {
    id: 'review-2',
    listingId: 'desert-retreat',
    author: 'Santiago',
    avatar: 'https://images.unsplash.com/photo-1544723795-3fb6469f5b39',
    rating: 5,
    createdAt: formatISO(addDays(new Date(), -34)),
    body: 'Loved the solar power story and open sky nights. The plunge pool was an ideal surprise after long hikes.',
    scores: {
      cleanliness: 5,
      accuracy: 4,
      communication: 5,
      location: 5,
      checkIn: 4,
      value: 5
    }
  }
];

export const wishlists: Wishlist[] = [
  {
    id: 'wishlist-coast',
    name: 'Coastal Escapes',
    isPrivate: false,
    coverPhoto: listings[0]?.photos[0],
    listingIds: ['harbor-loft']
  }
];

export const threads: MessageThread[] = [
  {
    id: 'thread-1',
    listingId: 'harbor-loft',
    participants: ['guest@harborhomes.dev', 'host@harborhomes.dev'],
    lastMessageAt: formatISO(addDays(new Date(), -3)),
    unreadCount: 1,
    messages: [
      {
        id: 'message-1',
        author: 'guest@harborhomes.dev',
        body: 'Hi Lena! Could we check in a bit early on Friday?',
        createdAt: formatISO(addDays(new Date(), -5))
      },
      {
        id: 'message-2',
        author: 'host@harborhomes.dev',
        body: 'Hello! Early check-in is no problem—arrive anytime after 1pm.',
        createdAt: formatISO(addDays(new Date(), -3))
      }
    ]
  }
];

export const trips: Trip[] = [
  {
    id: 'trip-1',
    listingId: 'desert-retreat',
    startDate: formatISO(addDays(new Date(), 15)),
    endDate: formatISO(addDays(new Date(), 18)),
    status: 'upcoming'
  },
  {
    id: 'trip-2',
    listingId: 'harbor-loft',
    startDate: formatISO(addDays(new Date(), -120)),
    endDate: formatISO(addDays(new Date(), -115)),
    status: 'completed'
  }
];
