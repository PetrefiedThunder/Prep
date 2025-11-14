'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Heart, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';
import { usePathname } from 'next/navigation';
import { formatCurrency } from '@/lib/currency';
import type { Listing } from '@/lib/types';

export interface ListingCardProps {
  listing: Listing;
  selected?: boolean;
  onHover?: () => void;
}

export const ListingCard = ({ listing, selected, onHover }: ListingCardProps) => {
  const pathname = usePathname();
  const locale = pathname.split('/')[1] || 'en';

  return (
    <motion.article
      whileHover={{ y: -4 }}
      className={`group relative flex flex-col gap-3 rounded-3xl border border-border/80 bg-white p-3 shadow-sm transition ${
        selected ? 'ring-2 ring-brand' : ''
      }`}
      onMouseEnter={onHover}
    >
    <div className="relative overflow-hidden rounded-3xl">
      <Image
        src={listing.photos[0] ?? '/placeholder.jpg'}
        alt={listing.title}
        width={720}
        height={540}
        className="h-48 w-full object-cover transition group-hover:scale-105"
        priority={listing.featured}
      />
      <button
        className="focus-ring absolute right-4 top-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/90 text-ink"
        aria-label="Save home"
      >
        <Heart className="h-5 w-5" />
      </button>
    </div>
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-sm text-muted-ink">
        <span className="inline-flex items-center gap-1">
          <MapPin className="h-4 w-4" />
          {listing.city}, {listing.country}
        </span>
        <span className="font-semibold text-ink">
          {listing.rating.toFixed(2)} ({listing.reviewCount})
        </span>
      </div>
      <Link href={`/${locale}/listing/${listing.id}`} className="text-base font-semibold text-ink hover:text-brand">
        {listing.title}
      </Link>
      <div className="text-sm text-muted-ink">
        {listing.beds} beds · {listing.baths} baths · sleeps {listing.guests}
      </div>
      <div className="mt-2 text-sm font-medium text-ink">
        {formatCurrency(listing.pricePerNight)} <span className="text-muted-ink">night</span>
      </div>
    </div>
    </motion.article>
  );
};
