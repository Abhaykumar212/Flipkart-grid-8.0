import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { ThumbsUp, ChevronDown } from "lucide-react";
import type { RatingBreakdown, Review } from "../../types/product";
import { RatingStars } from "../ui/RatingStars";
import { formatIndianNumber } from "../../lib/format";
import { useTracker } from "../../context/TrackerContext";
import { pageContext } from "../../lib/pageContext";
import { InlineHighlight } from "../intervention/InlineHighlight";
import { useInlineTarget } from "../intervention/useInlineTarget";
import { useIntervention } from "../../context/InterventionContext";
import { rankReviewsForDiagnosis } from "../../lib/adaptiveContent";

interface RatingsAndReviewsProps {
  productId: string;
  ratingDistribution: RatingBreakdown[];
  reviews: Review[];
  /** Real per-product spec highlights — what makes the AI summary specific to this item, not the category. */
  highlights: string[];
}

const reviewDateFormat = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const PAGE_SIZE = 3;
const TRUNCATE_AT = 150;

function ReviewCard({ review }: { review: Review }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = review.text.length > TRUNCATE_AT;
  const shownText = isLong && !expanded ? `${review.text.slice(0, TRUNCATE_AT).trimEnd()}…` : review.text;

  return (
    <article className="py-4 first:pt-0">
      <div className="flex items-center gap-2">
        <RatingStars value={review.rating} variant="pill" size="sm" />
        <h3 className="text-fk-md font-medium text-fk-ink">{review.title}</h3>
      </div>
      <p className="mt-1.5 text-fk-base text-fk-ink">
        {shownText}
        {isLong && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="ml-1.5 font-medium text-fk-blue"
          >
            {expanded ? "Read less" : "Read more"}
          </button>
        )}
      </p>
      <div className="mt-2 flex items-center gap-4 text-fk-sm text-fk-muted">
        <span className="font-medium text-fk-ink">{review.reviewerName}</span>
        <span>{reviewDateFormat.format(new Date(review.date))}</span>
        <span className="ml-auto flex items-center gap-1">
          <ThumbsUp className="h-3.5 w-3.5" strokeWidth={2} />
          {formatIndianNumber(review.helpfulCount)}
        </span>
      </div>
    </article>
  );
}

export function RatingsAndReviews({ productId, ratingDistribution, reviews, highlights }: RatingsAndReviewsProps) {
  const sorted = [...ratingDistribution].sort((a, b) => b.stars - a.stars);
  const max = Math.max(...sorted.map((r) => r.count), 1);
  const sectionRef = useRef<HTMLElement>(null);
  const recorded = useRef(false);
  const { recordReviewVisibility } = useTracker();
  const { diagnosis } = useIntervention();
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [showAiSummary, setShowAiSummary] = useState(false);
  const headerInline = useInlineTarget("reviews-header");

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !recorded.current) {
          recorded.current = true;
          recordReviewVisibility(reviews.length);
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(section);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    let dwellTimer: number | null = null;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          dwellTimer = window.setTimeout(() => {
            pageContext.markReviewDwell(productId);
            setShowAiSummary(true);
          }, 2000);
        } else if (dwellTimer !== null) {
          window.clearTimeout(dwellTimer);
          dwellTimer = null;
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(section);
    return () => {
      observer.disconnect();
      if (dwellTimer !== null) window.clearTimeout(dwellTimer);
    };
  }, [productId]);

  const orderedReviews = rankReviewsForDiagnosis(
    reviews,
    diagnosis?.productId === productId ? diagnosis.analysis : null,
  );
  const visibleReviews = orderedReviews.slice(0, visibleCount);
  const remaining = orderedReviews.length - visibleReviews.length;

  const showMore = () => {
    setVisibleCount((v) => Math.min(reviews.length, v + PAGE_SIZE));
    recordReviewVisibility();
  };

  // Product-specific, not category-generic: pros come from this product's own
  // spec highlights, the caveat from whichever review buyers actually voted
  // most helpful — never a fixed "AMOLED display, low-light camera" blurb
  // that happened to show up on a pair of headphones.
  const summaryPros = highlights.slice(0, 3);
  const mostHelpful = [...reviews].sort((a, b) => b.helpfulCount - a.helpfulCount)[0];

  return (
    <section
      ref={sectionRef}
      className="rounded-[2px] bg-white p-6"
      data-testid="reviews-section"
      id="customer-reviews"
    >
      {(() => {
        const heading = (
          <h2 ref={headerInline.anchorRef} className="mb-4 text-fk-xl font-medium text-fk-ink">
            Ratings &amp; Reviews
          </h2>
        );
        return (
          <AnimatePresence mode="wait" initial={false}>
            {headerInline.isActive && headerInline.content ? (
              <InlineHighlight key="highlighted" {...headerInline.content}>
                {heading}
              </InlineHighlight>
            ) : (
              <div key="plain">{heading}</div>
            )}
          </AnimatePresence>
        );
      })()}

      {showAiSummary && (
        <div className="mb-6 rounded-2xl border-2 border-fk-blue/40 bg-gradient-to-r from-blue-50/90 to-indigo-50/90 p-4 shadow-md backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-500">
          <div className="mb-2 flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-sm">
              ✨ AI Intervention: Verified Buyer Review Summary
            </span>
            <span className="text-[11px] font-bold text-fk-blue">Based on {reviews.length}+ verified buyer reviews</span>
          </div>
          <h4 className="text-fk-md font-bold text-fk-ink">AI Insights &amp; Sentiment Highlights</h4>
          <div className="mt-2.5 grid grid-cols-1 gap-3 sm:grid-cols-2 text-fk-sm text-fk-ink/90">
            <div className="rounded-xl bg-white/90 p-3 border border-emerald-200 shadow-sm">
              <span className="font-bold text-emerald-700">👍 Top Verified Pros</span>
              {summaryPros.length > 0 ? (
                <ul className="mt-1.5 flex flex-col gap-1">
                  {summaryPros.map((pro) => (
                    <li key={pro} className="flex items-start gap-1.5">
                      <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-emerald-600" />
                      <span>{pro}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1.5">Consistently praised for reliability and value in its category.</p>
              )}
            </div>
            <div className="rounded-xl bg-white/90 p-3 border border-amber-200 shadow-sm">
              <span className="font-bold text-amber-700">⚡ Most helpful buyer review</span>
              {mostHelpful ? (
                <p className="mt-1.5">
                  <span className="font-medium text-fk-ink">"{mostHelpful.title}"</span> — {mostHelpful.text}{" "}
                  <span className="text-fk-xs text-fk-muted">
                    ({formatIndianNumber(mostHelpful.helpfulCount)} found this helpful)
                  </span>
                </p>
              ) : (
                <p className="mt-1.5">No reviews yet — be the first to share your experience.</p>
              )}
            </div>
          </div>
        </div>
      )}

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

        <div>
          <div className="flex flex-col divide-y divide-fk-border">
            {visibleReviews.map((review) => (
              <ReviewCard key={review.id} review={review} />
            ))}
          </div>

          {remaining > 0 && (
            <button
              onClick={showMore}
              data-testid="show-more-reviews-button"
              className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-[2px] border border-fk-border py-2.5 text-fk-md font-medium text-fk-blue hover:bg-fk-bg"
            >
              Show More Reviews ({remaining} more)
              <ChevronDown className="h-4 w-4" strokeWidth={2.5} />
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
