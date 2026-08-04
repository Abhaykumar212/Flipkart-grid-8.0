import type { RootCauseAnalysis } from "./pipelineTrace";
import type { Review, SpecSection } from "../types/product";

const REVIEW_CONCERNS = [
  "assured",
  "battery",
  "camera",
  "charging",
  "comfort",
  "connectivity",
  "delivery",
  "display",
  "durability",
  "fit",
  "genuine",
  "heating",
  "original",
  "performance",
  "quality",
  "replacement",
  "return",
  "seller",
  "service",
  "sound",
  "support",
  "value",
  "warranty",
] as const;

const DEFAULT_REVIEW_CONCERNS: Record<string, readonly string[]> = {
  product_uncertainty: ["performance", "battery", "camera", "display", "quality", "fit", "value"],
  trust_friction: ["seller", "genuine", "original", "assured", "warranty", "replacement", "return", "support", "quality"],
};

const SPEC_CONCERNS = [
  "audio",
  "battery",
  "camera",
  "charging",
  "connectivity",
  "cooling",
  "delivery",
  "design",
  "display",
  "graphics",
  "installation",
  "material",
  "memory",
  "performance",
  "processor",
  "sound",
  "storage",
  "warranty",
] as const;

function analysisText(analysis: RootCauseAnalysis): string {
  const primary = analysis.primary_root_cause;
  return [
    primary.category,
    primary.headline,
    primary.explanation,
    analysis.shopper_narrative,
    ...primary.supporting_evidence.flatMap((evidence) => [
      evidence.signal,
      evidence.observed_value,
      evidence.why_it_matters,
    ]),
    ...analysis.contributing_factors.flatMap((factor) => [
      factor.category,
      factor.headline,
      factor.signal,
    ]),
  ]
    .join(" ")
    .toLowerCase()
    .replaceAll("_", " ");
}

function occurrences(text: string, keyword: string): number {
  let count = 0;
  let fromIndex = 0;
  while (fromIndex < text.length) {
    const match = text.indexOf(keyword, fromIndex);
    if (match < 0) break;
    count += 1;
    fromIndex = match + keyword.length;
  }
  return count;
}

/**
 * Passive content adaptation only: this changes the order of reviews already
 * present on the PDP. It deliberately does not call selectSurface or consume
 * fatigue budget because no intervention is being rendered.
 */
export function rankReviewsForDiagnosis(
  reviews: Review[],
  analysis: RootCauseAnalysis | null,
): Review[] {
  if (!analysis) return reviews;

  const categories = [
    analysis.primary_root_cause.category,
    ...analysis.contributing_factors.map((factor) => factor.category),
  ].filter(
    (category): category is "product_uncertainty" | "trust_friction" =>
      category === "product_uncertainty" || category === "trust_friction",
  );
  if (categories.length === 0) return reviews;

  const diagnosis = analysisText(analysis);
  const explicit = REVIEW_CONCERNS.filter((keyword) => diagnosis.includes(keyword));
  const defaults = categories.flatMap((category) => DEFAULT_REVIEW_CONCERNS[category]);
  const keywords = [...new Set([...explicit, ...defaults])];

  return reviews
    .map((review, index) => {
      const text = `${review.title} ${review.text}`.toLowerCase();
      const score = keywords.reduce((total, keyword) => total + occurrences(text, keyword), 0);
      return { review, index, score };
    })
    .sort((left, right) => right.score - left.score || left.index - right.index)
    .map(({ review }) => review);
}

/**
 * Passive content adaptation only: move an existing specification section to
 * the front when the diagnosis names that concern. This is content ordering,
 * not an intensity-ladder intervention, so it spends no fatigue budget.
 */
export function rankSpecSectionsForDiagnosis(
  sections: SpecSection[],
  analysis: RootCauseAnalysis | null,
): SpecSection[] {
  if (!analysis || sections.length < 2) return sections;

  const diagnosis = analysisText(analysis);
  const concerns = SPEC_CONCERNS.filter((keyword) => diagnosis.includes(keyword));
  if (concerns.length === 0) return sections;

  const scored = sections.map((section, index) => {
    const searchable = [
      section.section,
      ...section.items.flatMap((item) => [item.label, item.value]),
    ]
      .join(" ")
      .toLowerCase();
    const score = concerns.reduce(
      (total, keyword) => total + occurrences(searchable, keyword),
      0,
    );
    return { section, index, score };
  });
  const best = [...scored].sort(
    (left, right) => right.score - left.score || left.index - right.index,
  )[0];
  if (best.score === 0 || best.index === 0) return sections;

  return [best.section, ...sections.filter((_, index) => index !== best.index)];
}
