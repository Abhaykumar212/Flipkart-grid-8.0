import type {
  Product,
  SpecSection,
  Seller,
  RatingBreakdown,
  Review,
  CategorySlug,
} from "../types/product";

/**
 * Fallback PDP-detail generator, used only when a product doesn't carry its
 * own hand-authored `specifications` / `description` / `seller` /
 * `ratingDistribution` / `reviews`. Everything here is derived deterministically
 * from the product's own id/rating/highlights via a seeded PRNG, so a given
 * product always renders the same generated content on every load — nothing
 * here uses `Math.random()` or changes between renders.
 *
 * This exists so every product in the catalog has a fully-populated PDP
 * without hand-authoring reviews/specs for all 50 — the 10 flagship products
 * keep their real hand-written detail untouched (`product.X ?? generateX(product)`).
 */

// ─── Seeded PRNG ────────────────────────────────────────────────────────────

function hashString(input: string): number {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/** mulberry32 — small, fast, deterministic PRNG seeded from a string. */
function seededRng(seed: string): () => number {
  let state = hashString(seed);
  return () => {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pickOne<T>(rng: () => number, items: readonly T[]): T {
  return items[Math.floor(rng() * items.length) % items.length];
}

/** Fisher-Yates using the seeded rng, so selection order is stable per product. */
function pickMany<T>(rng: () => number, items: readonly T[], count: number): T[] {
  const pool = [...items];
  const result: T[] = [];
  for (let i = 0; i < count && pool.length > 0; i++) {
    const index = Math.floor(rng() * pool.length);
    result.push(pool.splice(index, 1)[0]);
  }
  return result;
}

function shortTitle(product: Product): string {
  return product.title.split(",")[0].split(" (")[0].trim();
}

// ─── Specifications ─────────────────────────────────────────────────────────

/**
 * Positional labels for each subCategory's `highlights` entries — verified
 * against the authoring order used across the catalog (e.g. phones are always
 * [storage, display, camera, (processor/battery)]).
 */
const SUBCATEGORY_SPEC_LABELS: Record<string, string[]> = {
  Smartphones: ["Memory & Storage", "Display", "Camera", "Processor & Battery"],
  "Gaming Laptops": ["Processor", "Memory & Storage", "Display", "Graphics"],
  "Thin and Light Laptops": ["Processor", "Memory & Storage", "Display", "Additional Feature"],
  Televisions: ["Display", "Sound", "Smart Features"],
  Headphones: ["Audio Feature", "Battery & Connectivity", "Charging"],
  Neckbands: ["Battery Life", "Audio Feature", "Charging"],
  "True Wireless Earbuds": ["Battery Life", "Audio Feature", "Connectivity & Resistance"],
  Refrigerators: ["Capacity", "Star Rating & Defrosting", "Compressor", "Special Feature"],
  "Washing Machines": ["Capacity & Load Type", "Wash Technology", "Special Feature"],
  "Microwave Ovens": ["Capacity", "Cooking Modes", "Special Feature"],
  Fans: ["Sweep Size", "Motor Type", "Warranty"],
  "Water Heaters": ["Capacity", "Heating Element", "Build"],
  "Kitchen Appliances": ["Motor Power", "Accessories", "Warranty"],
  "Vacuum Cleaners": ["Suction Power", "Special Feature", "Connectivity"],
  "Air Conditioners": ["Capacity & Rating", "Technology", "Condenser"],
  Coolers: ["Capacity", "Type", "Power Consumption"],
  "Water Purifiers": ["Storage Capacity", "Purification Technology", "Maintenance"],
  "Casual Shoes": ["Upper & Closure", "Sole", "Best For"],
  "Sports Shoes": ["Upper & Closure", "Sole", "Best For"],
  "T-Shirts": ["Fabric", "Neck Style", "Fit"],
  Jeans: ["Fit", "Fabric", "Care Instructions"],
  "Formal Shirts": ["Fabric", "Fit", "Care Instructions"],
  "Bags & Backpacks": ["Capacity", "Material", "Special Feature"],
  Kurtas: ["Print / Pattern", "Fit", "Fabric"],
};

const GENERIC_SPEC_LABELS = ["Feature 1", "Feature 2", "Feature 3", "Feature 4"];

export function generateSpecifications(product: Product): SpecSection[] {
  const labels = SUBCATEGORY_SPEC_LABELS[product.subCategory] ?? GENERIC_SPEC_LABELS;

  return [
    {
      section: "General",
      items: [
        { label: "Brand", value: product.brand },
        { label: "Category", value: product.subCategory },
        {
          label: "In The Box",
          value: `1 ${shortTitle(product)}, User Guide, Warranty Card`,
        },
      ],
    },
    {
      section: "Key Specifications",
      items: product.highlights.map((value, i) => ({
        label: labels[i] ?? `Feature ${i + 1}`,
        value,
      })),
    },
  ];
}

// ─── Description ─────────────────────────────────────────────────────────────

const CATEGORY_OPENERS: Record<CategorySlug, (p: Product) => string> = {
  mobiles: (p) =>
    `The ${shortTitle(p)} is built for everyday use, pairing a capable ${p.subCategory.toLowerCase()} experience with the specs that matter most day to day — display quality, camera performance, and battery life.`,
  electronics: (p) =>
    `This ${p.brand} ${p.subCategory.toLowerCase().slice(0, -1)} is designed for reliable daily use, whether that means powering through work and entertainment or handling a demanding household without fuss.`,
  audio: (p) =>
    `The ${shortTitle(p)} focuses on what actually matters in a pair of ${p.subCategory.toLowerCase()}: a comfortable long-wear fit, dependable battery life, and sound that holds up outside a lab test.`,
  appliances: (p) =>
    `Built by ${p.brand}, this ${p.subCategory.toLowerCase().slice(0, -1)} is meant to disappear into the daily household routine — dependable performance without needing constant attention.`,
  fashion: (p) =>
    `This ${p.brand} piece is made for everyday wear, balancing comfort and style without asking you to compromise on either.`,
};

const CLOSING_LINES = [
  "A solid choice if you want dependable performance without stretching the budget.",
  "Reviewed favorably by shoppers who value straightforward, no-nonsense performance over flashy extras.",
  "Fits naturally into daily use without demanding a learning curve.",
  "Backed by consistent quality checks, it's a dependable pick in its segment.",
  "Delivers on the essentials, which is exactly what most buyers are looking for at this price.",
];

export function generateDescription(product: Product): string {
  const opener = CATEGORY_OPENERS[product.category](product);
  const rng = seededRng(`${product.id}:description`);
  const highlightLine =
    product.highlights.length > 0
      ? ` Highlights include ${product.highlights.slice(0, 2).join(" and ")}.`
      : "";
  const closing = pickOne(rng, CLOSING_LINES);
  return `${opener}${highlightLine} ${closing}`;
}

// ─── Seller ──────────────────────────────────────────────────────────────────

const GENERIC_SELLERS = [
  "RetailNet",
  "SuperComNet",
  "UrbanTradeLink",
  "OmniMart Wholesale",
  "PrimeCart Retail",
  "Metro Seller Hub",
  "TrustBazaar",
  "Value Mart Traders",
  "QuickShip Commerce",
  "NextGen Retailers",
];

export function generateSeller(product: Product): Seller {
  const rng = seededRng(`${product.id}:seller`);
  const name = pickOne(rng, GENERIC_SELLERS);
  const rating = Math.round(Math.min(4.8, Math.max(3.6, product.rating.value - 0.2 + rng() * 0.4)) * 10) / 10;
  return { name, rating };
}

// ─── Rating distribution ─────────────────────────────────────────────────────

/**
 * Real e-commerce rating distributions are J-shaped, not a symmetric bell
 * around the average — 5★ is almost always the tallest bar even when the
 * average sits around 4.2, because a handful of 1★ complaints drag the mean
 * down without ever outnumbering the happy majority. These two anchors
 * (a strong product and a mediocre one) get linearly interpolated by rating
 * value so the shape stays realistic across the catalog's 3.7–4.6 range.
 */
const DISTRIBUTION_HIGH = { 5: 0.68, 4: 0.2, 3: 0.07, 2: 0.03, 1: 0.02 };
const DISTRIBUTION_LOW = { 5: 0.35, 4: 0.3, 3: 0.2, 2: 0.09, 1: 0.06 };
const HIGH_ANCHOR = 4.6;
const LOW_ANCHOR = 3.7;

export function generateRatingDistribution(product: Product): RatingBreakdown[] {
  const { value, count } = product.rating;
  const stars = [5, 4, 3, 2, 1] as const;

  const t = Math.min(1, Math.max(0, (value - LOW_ANCHOR) / (HIGH_ANCHOR - LOW_ANCHOR)));
  const weights = stars.map((s) => {
    const low = DISTRIBUTION_LOW[s];
    const high = DISTRIBUTION_HIGH[s];
    return low + t * (high - low);
  });
  const totalWeight = weights.reduce((a, b) => a + b, 0);

  const raw = weights.map((w) => (w / totalWeight) * count);
  const floored = raw.map(Math.floor);
  let remainder = count - floored.reduce((a, b) => a + b, 0);

  // Distribute leftover units to the stars with the largest fractional part.
  const order = raw
    .map((v, i) => ({ i, frac: v - floored[i] }))
    .sort((a, b) => b.frac - a.frac);
  for (const { i } of order) {
    if (remainder <= 0) break;
    floored[i] += 1;
    remainder -= 1;
  }

  return stars.map((s, i) => ({ stars: s, count: floored[i] }));
}

// ─── Reviews ─────────────────────────────────────────────────────────────────

interface ReviewTemplate {
  rating: number;
  title: string;
  text: string;
}

const REVIEW_TEMPLATES: Record<CategorySlug, ReviewTemplate[]> = {
  mobiles: [
    { rating: 5, title: "Exceeded expectations", text: "Been using it as my daily driver for a few weeks now — performance is smooth, camera handles low light better than I expected, and battery comfortably lasts a full day." },
    { rating: 5, title: "Great value for money", text: "For this price, the display and build quality feel like they belong in a higher segment. No complaints so far." },
    { rating: 4, title: "Solid phone, minor gripes", text: "Overall very happy with the purchase. Software has a couple of pre-installed apps I'd rather not have, but performance and camera are both good." },
    { rating: 4, title: "Good daily driver", text: "Handles calls, browsing, and casual gaming without any lag. Charging speed is decent, wish the bundled accessories were a bit better." },
    { rating: 3, title: "Does the job, nothing more", text: "It's an average phone for an average price. Gets warm during long calls and heavier apps, but otherwise reliable enough for daily tasks." },
    { rating: 3, title: "Decent but not amazing", text: "Camera performance drops noticeably in low light compared to what the marketing suggests. Fine for everyday use though." },
    { rating: 2, title: "Battery drains faster than expected", text: "Two weeks in and battery life has already started to disappoint with moderate use. Might just be my unit, but wanted to flag it." },
    { rating: 1, title: "Had to get a replacement", text: "Received a unit with a flickering display issue. Customer support handled the replacement fine, but the initial experience wasn't great." },
  ],
  electronics: [
    { rating: 5, title: "Runs everything smoothly", text: "Whether it's work, streaming, or the occasional game, this handles it without breaking a sweat. Build quality feels sturdy too." },
    { rating: 5, title: "Impressive for the price bracket", text: "Display quality and performance punch above what I expected at this price point. Very happy with the purchase." },
    { rating: 4, title: "Great performer, a few quirks", text: "Does what it promises — fast, reliable, good display. Fan noise kicks in under heavier load but isn't a dealbreaker." },
    { rating: 4, title: "Good buy overall", text: "Setup was quick and painless. Performance has been consistent for my daily workload with no slowdowns." },
    { rating: 3, title: "Average experience", text: "Does the basics well but nothing stands out. Fine if you're not expecting premium-tier polish." },
    { rating: 3, title: "Fine for casual use", text: "Handles everyday tasks fine, but starts to show its limits under heavier multitasking." },
    { rating: 2, title: "Warranty process was a hassle", text: "Faced a minor hardware issue in the first month and the support process took longer than expected to resolve." },
    { rating: 1, title: "Not what I expected", text: "Performance doesn't quite match the specs sheet. Might work better for someone with lighter usage needs." },
  ],
  audio: [
    { rating: 5, title: "Battery life is no joke", text: "Easily gets me through a full week of commuting on one charge. Sound is balanced without being overly bass-heavy." },
    { rating: 5, title: "Comfortable for long sessions", text: "Wore these through a full work day with zero discomfort. Call quality is clear too." },
    { rating: 4, title: "Solid sound, decent fit", text: "Audio quality is impressive for the price. Ear tips could offer a slightly better seal for true isolation." },
    { rating: 4, title: "Reliable daily use pair", text: "Connects instantly every time, battery holds up well. Would recommend for anyone who wants a no-fuss pair." },
    { rating: 3, title: "Gets the job done", text: "Sound is acceptable but doesn't stand out. Fine for casual listening, not for critical listening." },
    { rating: 3, title: "Average, does what's needed", text: "Bass could be punchier but overall a reasonable buy at this price point." },
    { rating: 2, title: "Connectivity drops occasionally", text: "Had a few random disconnects during calls. Might be device-specific but wanted to flag it." },
    { rating: 1, title: "One earbud stopped working", text: "Right earbud stopped charging properly within the first month. Getting it replaced under warranty." },
  ],
  appliances: [
    { rating: 5, title: "Works flawlessly so far", text: "Been using it daily for a couple of months with zero issues. Quiet operation and does exactly what it promises." },
    { rating: 5, title: "Great addition to the household", text: "Genuinely useful upgrade — noticeably better than what we had before. Installation was smooth too." },
    { rating: 4, title: "Happy with the purchase", text: "Performs reliably for daily use. Only minor gripe is the manual could be clearer on some settings." },
    { rating: 4, title: "Good value appliance", text: "Does the job well for the price. Nothing fancy, but dependable for daily household use." },
    { rating: 3, title: "Adequate for basic needs", text: "Handles the basics fine but don't expect premium-tier performance at this price." },
    { rating: 3, title: "Okay, not outstanding", text: "Works as expected, though a bit louder during operation than I'd like." },
    { rating: 2, title: "Installation took longer than expected", text: "Product itself is fine, but scheduling the installation appointment was a hassle." },
    { rating: 1, title: "Arrived with a minor defect", text: "Had to raise a replacement request within the first week due to a manufacturing issue." },
  ],
  fashion: [
    { rating: 5, title: "Great fit and quality", text: "Fabric feels good quality for the price and the fit is true to size. Would buy again." },
    { rating: 5, title: "Comfortable for daily wear", text: "Wearing this regularly and it's held up well after several washes. Looks as good as the photos." },
    { rating: 4, title: "Good buy, sizing runs slightly large", text: "Quality is solid for the price. Would recommend sizing down if you prefer a snug fit." },
    { rating: 4, title: "Happy with this purchase", text: "Fits well and the material feels durable. Good value for the price point." },
    { rating: 3, title: "Decent, nothing special", text: "Fit is okay, fabric feels average for the price. Wearable but not a standout piece." },
    { rating: 3, title: "As expected for the price", text: "Does the job as an everyday piece, though the color faded slightly after a few washes." },
    { rating: 2, title: "Fabric quality below expectations", text: "Feels thinner than expected from the photos. Fit is fine but material could be better." },
    { rating: 1, title: "Sizing was way off", text: "Ordered my usual size but it ran noticeably small. Had to request an exchange." },
  ],
};

const REVIEWER_NAMES = [
  "Aditya Sharma", "Priya Nair", "Rohit Verma", "Karan Mehta", "Sneha Iyer",
  "Ankit Joshi", "Divya Pillai", "Suresh Kumar", "Ramesh Iyer", "Anjali Desai",
  "Nikhil Bhatt", "Pooja Reddy", "Arjun Malhotra", "Fatima Sheikh", "Rahul Sood",
  "Neha Kapoor", "Deepak Nair", "Shalini Bhatt", "Vikram Rao", "Meera Krishnan",
  "Vivek Chandra", "Riya Sen", "Amit Trivedi", "Kavya Menon", "Siddharth Rao",
  "Ishita Bose", "Manish Agarwal", "Tanvi Shah", "Rajesh Pillai", "Sunita Verma",
  "Yash Kulkarni", "Aarti Singh", "Harsh Vardhan", "Preeti Chawla", "Gaurav Kapoor",
  "Nisha Thomas",
];

const REVIEWS_PER_PRODUCT = 6;
const DAY_OFFSETS = [4, 9, 15, 21, 29, 37, 44, 52];

export function generateReviews(product: Product): Review[] {
  const rng = seededRng(`${product.id}:reviews`);
  const templates = REVIEW_TEMPLATES[product.category];

  const chosenTemplates = pickMany(rng, templates, Math.min(REVIEWS_PER_PRODUCT, templates.length));
  const names = pickMany(rng, REVIEWER_NAMES, chosenTemplates.length);
  const offsets = pickMany(rng, DAY_OFFSETS, chosenTemplates.length);

  const popularityBase = Math.min(400, Math.max(8, Math.round(product.rating.count / 150)));

  return chosenTemplates
    .map((template, i) => {
      const date = new Date();
      date.setDate(date.getDate() - offsets[i]);
      const helpfulCount = Math.max(2, Math.round(popularityBase * (0.4 + rng() * 1.2)));

      return {
        id: `${product.id}-gen-${i}`,
        reviewerName: names[i],
        rating: template.rating,
        title: template.title,
        text: template.text,
        helpfulCount,
        date: date.toISOString().slice(0, 10),
      };
    })
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

// ─── Public accessors ────────────────────────────────────────────────────────

export function getSpecifications(product: Product): SpecSection[] {
  return product.specifications ?? generateSpecifications(product);
}

export function getDescription(product: Product): string {
  return product.description ?? generateDescription(product);
}

export function getSeller(product: Product): Seller {
  return product.seller ?? generateSeller(product);
}

export function getRatingDistribution(product: Product): RatingBreakdown[] {
  return product.ratingDistribution ?? generateRatingDistribution(product);
}

export function getReviews(product: Product): Review[] {
  return product.reviews ?? generateReviews(product);
}
