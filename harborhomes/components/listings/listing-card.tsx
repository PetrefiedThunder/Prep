"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { Heart, Star } from "lucide-react";
import type { Listing } from "@/lib/types";
import { useWishlistStore } from "@/store/wishlist-store";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/currency";

interface ListingCardProps {
  listing: Listing;
  href?: string;
  onHover?: (id: string | null) => void;
}

export function ListingCard({ listing, href = `/listing/${listing.id}`, onHover }: ListingCardProps) {
  const { saved, toggle } = useWishlistStore();
  const isSaved = saved.has(listing.id);

  return (
    <motion.article
      whileHover={{ y: -4 }}
      className="group relative overflow-hidden rounded-3xl border border-border bg-white shadow-sm transition"
      onHoverStart={() => onHover?.(listing.id)}
      onHoverEnd={() => onHover?.(null)}
    >
      <div className="relative aspect-[4/3] overflow-hidden">
        <Image
          src={listing.images[0]}
          alt={listing.title}
          fill
          className="object-cover transition duration-500 group-hover:scale-105"
          sizes="(min-width: 1024px) 320px, 100vw"
        />
        <button
          className="absolute right-3 top-3 rounded-full bg-white/80 p-2 text-ink shadow-sm transition hover:bg-white"
          aria-label={isSaved ? "Remove from wishlists" : "Save to wishlists"}
          onClick={(event) => {
            event.preventDefault();
            toggle(listing.id);
          }}
        >
          <Heart className={`h-5 w-5 ${isSaved ? "fill-brand text-brand" : "text-ink"}`} />
        </button>
      </div>
      <div className="flex flex-col gap-3 p-4">
        <div className="flex items-start justify-between">
          <div>
            <Link href={href} className="text-sm font-semibold text-ink">
              {listing.title}
            </Link>
            <p className="text-xs text-muted-ink">
              {listing.city}, {listing.country}
            </p>
          </div>
          <div className="flex items-center gap-1 text-sm text-ink">
            <Star className="h-4 w-4 fill-brand text-brand" />
            <span>{listing.rating.toFixed(2)}</span>
          </div>
        </div>
        <div>
          <p className="text-sm font-semibold text-ink">
            {formatCurrency(listing.nightlyPrice)}
            <span className="text-xs font-normal text-muted-ink"> / night</span>
          </p>
        </div>
        <Button asChild variant="secondary" className="rounded-2xl">
          <Link href={href}>View details</Link>
        </Button>
      </div>
    </motion.article>
  );
}
