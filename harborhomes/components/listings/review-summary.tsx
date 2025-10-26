import type { Review } from "@/lib/types";
import { Star } from "lucide-react";

export function ReviewSummary({ reviews }: { reviews: Review[] }) {
  if (!reviews.length) return null;

  const average =
    reviews.reduce((total, review) => total + (review.cleanliness + review.accuracy + review.communication + review.location + review.value) / 5, 0) /
    reviews.length;

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2 text-2xl font-semibold text-ink">
        <Star className="h-6 w-6 fill-brand text-brand" />
        <span>{average.toFixed(2)}</span>
        <span className="text-base text-muted-ink">· {reviews.length} reviews</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {reviews.map((review) => (
          <article key={review.id} className="rounded-3xl border border-border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <img src={review.author.avatar} alt={review.author.name} className="h-10 w-10 rounded-full object-cover" />
              <div>
                <p className="text-sm font-semibold">{review.author.name}</p>
                <p className="text-xs text-muted-ink">Stayed {new Date(review.createdAt).toLocaleDateString()}</p>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted-ink">{review.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
