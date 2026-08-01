import { ThumbsUp } from "lucide-react";
import type { RatingBreakdown, Review } from "../../types/product";
import { RatingStars } from "../ui/RatingStars";
import { formatIndianNumber } from "../../lib/format";

interface RatingsAndReviewsProps {
  ratingDistribution: RatingBreakdown[];
  reviews: Review[];
}

const reviewDateFormat = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function RatingsAndReviews({ ratingDistribution, reviews }: RatingsAndReviewsProps) {
  const sorted = [...ratingDistribution].sort((a, b) => b.stars - a.stars);
  const max = Math.max(...sorted.map((r) => r.count), 1);

  return (
    <section
      className="rounded-[2px] bg-white p-6"
      data-testid="reviews-section"
    >
      <h2 className="mb-4 text-fk-xl font-medium text-fk-ink">Ratings &amp; Reviews</h2>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[280px_1fr]">
        <div className="flex flex-col gap-2">
          {sorted.map(({ stars, count }) => (
            <div key={stars} className="flex items-center gap-2">
              <span className="w-14 shrink-0 text-fk-base text-fk-ink">{stars} ★</span>
              <div className="h-2 flex-1 rounded-full bg-fk-bg">
                <div
                  className="h-2 rounded-full bg-fk-green"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
              <span className="w-16 shrink-0 text-right text-fk-sm text-fk-muted">
                {formatIndianNumber(count)}
              </span>
            </div>
          ))}
        </div>

        <div className="flex flex-col divide-y divide-fk-border">
          {reviews.map((review) => (
            <article key={review.id} className="py-4 first:pt-0">
              <div className="flex items-center gap-2">
                <RatingStars value={review.rating} variant="pill" size="sm" />
                <h3 className="text-fk-md font-medium text-fk-ink">{review.title}</h3>
              </div>
              <p className="mt-1.5 text-fk-base text-fk-ink">{review.text}</p>
              <div className="mt-2 flex items-center gap-4 text-fk-sm text-fk-muted">
                <span className="font-medium text-fk-ink">{review.reviewerName}</span>
                <span>{reviewDateFormat.format(new Date(review.date))}</span>
                <span className="ml-auto flex items-center gap-1">
                  <ThumbsUp className="h-3.5 w-3.5" strokeWidth={2} />
                  {formatIndianNumber(review.helpfulCount)}
                </span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
