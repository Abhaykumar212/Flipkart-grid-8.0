import { useEffect, useMemo, useRef, useState } from "react";
import { BadgeCheck, ChevronDown, ThumbsUp } from "lucide-react";
import type { RatingBreakdown, Review } from "../../types/product";
import { RatingStars } from "../ui/RatingStars";
import { formatIndianNumber } from "../../lib/format";
import { useSession } from "../../context/SessionContext";
import { Button } from "../ui/Button";

interface RatingsAndReviewsProps {
  productId: string;
  ratingDistribution: RatingBreakdown[];
  reviews: Review[];
}

type ReviewSort = "recent" | "helpful" | "highest" | "lowest";

const PAGE_SIZE = 3;
const reviewDateFormat = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function RatingsAndReviews({ productId, ratingDistribution, reviews }: RatingsAndReviewsProps) {
  const sortedDistribution = [...ratingDistribution].sort((a, b) => b.stars - a.stars);
  const totalRatings = sortedDistribution.reduce((sum, item) => sum + item.count, 0);
  const average = totalRatings > 0
    ? sortedDistribution.reduce((sum, item) => sum + item.stars * item.count, 0) / totalRatings
    : 0;
  const max = Math.max(...sortedDistribution.map((item) => item.count), 1);
  const sectionRef = useRef<HTMLElement>(null);
  const recorded = useRef(false);
  const dwellStartedAt = useRef<number | null>(null);
  const { emit } = useSession();
  const [allReviews, setAllReviews] = useState(reviews);
  const [ratingFilter, setRatingFilter] = useState<number | null>(null);
  const [sort, setSort] = useState<ReviewSort>("recent");
  const [helpfulVotes, setHelpfulVotes] = useState<Record<string, number>>({});
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [writing, setWriting] = useState(false);
  const [reviewerName, setReviewerName] = useState("");
  const [reviewRating, setReviewRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [formMessage, setFormMessage] = useState("");

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;
    recorded.current = false;
    dwellStartedAt.current = null;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !recorded.current) {
        recorded.current = true;
        dwellStartedAt.current = performance.now();
        emit("REVIEW_OPENED", {
          productId,
          metadata: { source: "PRODUCT_PAGE" },
        });
        observer.disconnect();
      }
    }, { threshold: 0.35 });
    observer.observe(section);
    return () => {
      observer.disconnect();
      if (dwellStartedAt.current !== null) {
        emit("REVIEW_DWELL_RECORDED", {
          productId,
          metadata: { dwell_ms: Math.max(0, Math.round(performance.now() - dwellStartedAt.current)) },
        });
        dwellStartedAt.current = null;
      }
    };
  }, [emit, productId]);

  const sortedReviews = useMemo(() => {
    const filtered = ratingFilter
      ? allReviews.filter((review) => review.rating === ratingFilter)
      : allReviews;
    return [...filtered].sort((a, b) => {
      if (sort === "helpful") {
        return (b.helpfulCount + (helpfulVotes[b.id] ?? 0))
          - (a.helpfulCount + (helpfulVotes[a.id] ?? 0));
      }
      if (sort === "highest") return b.rating - a.rating;
      if (sort === "lowest") return a.rating - b.rating;
      return new Date(b.date).getTime() - new Date(a.date).getTime();
    });
  }, [allReviews, helpfulVotes, ratingFilter, sort]);

  const visibleReviews = sortedReviews.slice(0, visibleCount);
  const remaining = sortedReviews.length - visibleReviews.length;

  const resetPagination = () => setVisibleCount(PAGE_SIZE);

  const submitReview = (event: React.FormEvent) => {
    event.preventDefault();
    if (!reviewerName.trim() || reviewRating === 0 || reviewText.trim().length < 40) {
      setFormMessage("Add your name, select a rating, and write at least 40 characters.");
      return;
    }
    setAllReviews((current) => [{
      id: `local-review-${Date.now()}`,
      reviewerName: reviewerName.trim(),
      rating: reviewRating,
      title: "Customer review",
      text: reviewText.trim(),
      helpfulCount: 0,
      date: new Date().toISOString().slice(0, 10),
    }, ...current]);
    setReviewerName("");
    setReviewRating(0);
    setReviewText("");
    setFormMessage("Thank you. Your review has been added to this demo session.");
    setWriting(false);
    setRatingFilter(null);
    resetPagination();
  };

  const showMore = () => {
    setVisibleCount((current) => Math.min(sortedReviews.length, current + PAGE_SIZE));
    emit("REVIEW_OPENED", {
      productId,
      metadata: { source: "SHOW_MORE" },
    });
  };

  return (
    <section ref={sectionRef} className="rounded-[2px] bg-white p-4 sm:p-6" data-testid="reviews-section">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-fk-xl font-medium text-fk-ink">Ratings &amp; Reviews</h2>
        <Button variant="outline" size="sm" className="min-h-11" onClick={() => setWriting((current) => !current)}>{writing ? "Close" : "Write a Review"}</Button>
      </div>

      {writing && (
        <form onSubmit={submitReview} className="mt-4 border border-fk-border bg-fk-bg p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-fk-sm font-medium text-fk-ink">Your name<input name="reviewerName" autoComplete="name" value={reviewerName} onChange={(event) => setReviewerName(event.target.value)} className="mt-1 h-12 w-full border border-fk-border bg-white px-3 text-base focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue" /></label>
            <fieldset><legend className="text-fk-sm font-medium text-fk-ink">Your rating</legend><div className="mt-1 flex gap-2">{[1, 2, 3, 4, 5].map((rating) => <button type="button" key={rating} onClick={() => setReviewRating(rating)} aria-label={`${rating} stars`} aria-pressed={reviewRating === rating} className={`h-12 w-12 border text-fk-md font-medium ${reviewRating === rating ? "border-fk-blue bg-fk-blue text-white" : "border-fk-border bg-white text-fk-ink"}`}>{rating}★</button>)}</div></fieldset>
          </div>
          <label className="mt-4 block text-fk-sm font-medium text-fk-ink">Review<textarea name="review" value={reviewText} maxLength={500} onChange={(event) => setReviewText(event.target.value)} className="mt-1 min-h-28 w-full resize-y border border-fk-border bg-white p-3 text-base focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue" placeholder="Tell shoppers what worked well and what could be better." /></label>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3"><span className="text-fk-sm text-fk-muted">{reviewText.length} / 500 characters</span><Button type="submit" className="min-h-11">Submit Review</Button></div>
          <p className={`mt-2 min-h-5 text-fk-sm ${formMessage.startsWith("Thank") ? "text-fk-green" : "text-fk-flame"}`} role="status">{formMessage}</p>
        </form>
      )}

      {!writing && formMessage.startsWith("Thank") && <p className="mt-3 text-fk-sm text-fk-green" role="status">{formMessage}</p>}

      <div className="mt-5 grid grid-cols-1 gap-8 lg:grid-cols-[300px_1fr]">
        <div>
          <div className="mb-5 flex items-center gap-3"><strong className="text-3xl font-medium text-fk-ink">{average.toFixed(1)}</strong><span><RatingStars value={average} variant="stars" /><span className="mt-1 block text-fk-sm text-fk-muted">{formatIndianNumber(totalRatings)} ratings</span></span></div>
          <div className="flex flex-col gap-1">
            {sortedDistribution.map(({ stars, count }) => (
              <button key={stars} type="button" onClick={() => { setRatingFilter((current) => current === stars ? null : stars); resetPagination(); }} aria-pressed={ratingFilter === stars} className={`flex min-h-11 items-center gap-2 rounded-[2px] px-2 text-left ${ratingFilter === stars ? "bg-blue-50" : "hover:bg-fk-bg"}`}>
                <span className="w-10 shrink-0 text-fk-base text-fk-ink">{stars} ★</span>
                <span className="h-2 flex-1 rounded-full bg-fk-bg"><span className="block h-2 rounded-full bg-fk-green" style={{ width: `${(count / max) * 100}%` }} /></span>
                <span className="w-16 shrink-0 text-right text-fk-sm text-fk-muted">{formatIndianNumber(count)}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 border-b border-fk-border pb-3">
            <p className="text-fk-base text-fk-muted">Showing {visibleReviews.length} {ratingFilter ? `${ratingFilter}-star ` : ""}reviews</p>
            <select value={sort} onChange={(event) => { setSort(event.target.value as ReviewSort); resetPagination(); }} className="h-11 border border-fk-border bg-white px-3 text-fk-base focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue" aria-label="Sort reviews"><option value="recent">Most Recent</option><option value="helpful">Most Helpful</option><option value="highest">Highest Rating</option><option value="lowest">Lowest Rating</option></select>
          </div>
          <div className="flex flex-col divide-y divide-fk-border">
            {visibleReviews.map((review) => (
              <article key={review.id} className="py-4 first:pt-0">
                <div className="flex items-center gap-2"><RatingStars value={review.rating} variant="pill" size="sm" /><h3 className="text-fk-md font-medium text-fk-ink">{review.title}</h3></div>
                <p className="mt-1.5 text-fk-base leading-5 text-fk-ink">{review.text}</p>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-fk-sm text-fk-muted"><span className="font-medium text-fk-ink">{review.reviewerName}</span><span className="inline-flex items-center gap-1 text-fk-green"><BadgeCheck className="h-3.5 w-3.5" />Certified Buyer</span><span>{reviewDateFormat.format(new Date(review.date))}</span><button type="button" onClick={() => setHelpfulVotes((current) => current[review.id] ? current : { ...current, [review.id]: 1 })} disabled={Boolean(helpfulVotes[review.id])} className="ml-auto flex min-h-11 items-center gap-1 px-2 hover:text-fk-blue disabled:text-fk-green" aria-label={`Mark review by ${review.reviewerName} helpful`}><ThumbsUp className="h-4 w-4" />Helpful ({formatIndianNumber(review.helpfulCount + (helpfulVotes[review.id] ?? 0))})</button></div>
              </article>
            ))}
            {visibleReviews.length === 0 && <div className="py-8 text-center text-fk-base text-fk-muted">No reviews match this rating. <button type="button" onClick={() => { setRatingFilter(null); resetPagination(); }} className="font-medium text-fk-blue">Show all reviews</button></div>}
          </div>
          {remaining > 0 && (
            <button type="button" onClick={showMore} data-testid="show-more-reviews-button" className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-[2px] border border-fk-border py-2.5 text-fk-md font-medium text-fk-blue hover:bg-fk-bg">
              Show More Reviews ({remaining} more)
              <ChevronDown className="h-4 w-4" strokeWidth={2.5} />
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
