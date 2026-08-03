# System Audit — FlipkartGridd

Read-only snapshot of the repository as it stands on `main` (commit range through
`d974240`, "Implement persistent AI Shopping Companion with proactive
interventions"), with targeted updates layered on top for the SQLite persistence
layer (`backend/db.py`, `backend/ledger.py`) added afterward — those sections are
current as of the working tree, not commit `d974240`; the rest of the document was
not re-verified against `d974240` and may have drifted further. No code was changed
to produce this document. Where something was planned but built differently, or not
built at all, that is called out explicitly rather than smoothed over.

---

## 1. Repo Layout

**This is a single monorepo, not two repos.** The Python backend, the ML
pipeline, and the React frontend all live in one git repository at
`C:\Users\Lakshay\Desktop\FlipkartGridd`. `README.md` (root) describes the
frontend as if it were a nested `Flipkart-grid-8.0/src/` directory and tells
you to run `npm --prefix Flipkart-grid-8.0 run dev` — that layout does not
exist. `src/` is at the repo root, as shown below. This is a real, load-bearing
inaccuracy in the README (see §10).

```text
FlipkartGridd/
├── backend/                     FastAPI app (Python 3.9/3.10)
│   ├── main.py                  all routes
│   ├── config.py                env vars, thresholds, model config
│   ├── schemas.py               shared pydantic models
│   ├── trace.py                 span recorder for the pipeline console
│   ├── db.py                    SQLite connection + schema (see §9a — new)
│   ├── ledger.py                delivery-decision write/read path (see §9a — new)
│   ├── data/                    gitignored; app.db lives here at runtime (new)
│   └── agents/
│       ├── gate.py              RCA trigger policy (pure, unit-tested; now SQLite-backed)
│       ├── root_cause.py        prompt assembly + Groq call for RCA
│       ├── intervention.py      deterministic lever scoring/ranking
│       ├── companion_chat.py    prompt assembly + Groq call for the chat widget
│       ├── levers.py            closed catalog of 14 intervention levers
│       ├── memory.py            per-session intervention feedback memory (now SQLite-backed)
│       └── README.md            Phase 2 design writeup (see §9)
├── ml/
│   ├── generate_dataset.py      synthetic dataset generator
│   ├── train_model.py           XGBoost + calibration + SHAP training script
│   ├── feature_engineering.py   raw → engineered feature transform
│   ├── data/cart_abandonment_dataset.csv   200,000 rows (generated, present)
│   ├── artifacts/               model.joblib, explainer.joblib, calibrator.joblib,
│   │                            feature_names.json, metrics.json (all present)
│   └── MODEL_CARD.md
├── src/                         React 18 + TypeScript + Vite frontend
│   ├── components/              cart, checkout, companion, home, layout, pdp,
│   │                            pipeline, ui  (28 .tsx files)
│   ├── context/                 CartContext, WishlistContext, TrackerContext
│   ├── data/                    products.ts, categories.ts, banners.ts,
│   │                            demoScenarios.ts, session.ts (unused — see §2)
│   ├── lib/                     tracker.ts, pipelineTrace.ts, pageContext.ts,
│   │                            userHistory.ts, companionChat.ts, cartTotals.ts,
│   │                            format.ts, productDetails.ts, fatigueBudget.ts (new),
│   │                            interventionLedger.ts (new), interventionPolicy.ts (new),
│   │                            interventionTargets.ts (new), targetRegistry.ts (new)
│   ├── routes/                  Home, ProductDetail, CartPage, CheckoutPage,
│   │                            SearchResultsPage, PipelineConsole
│   └── types/product.ts
├── tests/                       Python unittest suite (4 files, see §9)
├── package.json                 no test script defined (see §10)
├── requirements.txt             fastapi, uvicorn, pydantic, numpy, pandas,
│                                 scikit-learn, xgboost, shap, joblib, python-dotenv
├── .env / .env.example
└── README.md                    stale — describes Phase 1 only, wrong paths
```

`node_modules`, `venv`/`__pycache__`, and `.git` are omitted above.

---

## 2. Data Model

### `src/types/product.ts` — full contents, verbatim

```typescript
/**
 * Product shape mirrors Flipkart's listing payload closely enough that the UI
 * reads as real inventory, while `signals` gives the cart-abandonment agent a
 * typed extension surface it can populate without a data migration.
 */

export type CategorySlug =
  | "mobiles"
  | "electronics"
  | "audio"
  | "appliances"
  | "fashion";

export interface Price {
  mrp: number;
  sellingPrice: number;
  currency: "INR";
}

export interface Rating {
  value: number;
  /** Number of star ratings. */
  count: number;
  /** Number of written reviews. */
  reviewCount: number;
}

export interface Badges {
  assured: boolean;
  bestseller: boolean;
  sponsored: boolean;
}

export interface Delivery {
  free: boolean;
  estimatedDays: number;
  express: boolean;
}

export interface Emi {
  monthly: number;
  months: number;
}

export interface Stock {
  inStock: boolean;
  quantityLeft: number;
}

export interface PricePoint {
  /** ISO date. */
  date: string;
  price: number;
}

/**
 * Behavioural signals consumed by the cart-abandonment agent. Every field is
 * optional-by-construction at the product level (`Product.signals?`) so the
 * catalog stays valid before any telemetry has been recorded.
 */
export interface ProductSignals {
  viewCount: number;
  searchCount: number;
  /** ISO timestamp of the most recent product-page view. */
  lastViewedAt?: string;
  /** ISO timestamp of cart add — the abandonment anchor. */
  addedToCartAt?: string;
  removedFromCartAt?: string;
  /** Milliseconds the item has sat in the cart without checkout. */
  cartDwellMs?: number;
  /** Feeds price-drop intervention. */
  priceHistory: PricePoint[];
  /** 0-1, written by the agent. */
  abandonmentScore?: number;
}

export interface SpecSection {
  section: string;
  items: { label: string; value: string }[];
}

export interface Review {
  id: string;
  reviewerName: string;
  rating: number;
  title: string;
  text: string;
  helpfulCount: number;
  /** ISO date. */
  date: string;
}

export interface RatingBreakdown {
  stars: 5 | 4 | 3 | 2 | 1;
  count: number;
}

export interface Seller {
  name: string;
  rating: number;
}

export interface Product {
  id: string;
  slug: string;
  title: string;
  brand: string;
  category: CategorySlug;
  subCategory: string;
  images: string[];
  price: Price;
  rating: Rating;
  badges: Badges;
  delivery: Delivery;
  offers: string[];
  emi?: Emi;
  stock: Stock;
  highlights: string[];
  signals?: ProductSignals;
  /**
   * PDP-only detail fields. Optional like `signals` — only populated for a
   * handful of products; the PDP renders a lighter page when absent instead
   * of showing placeholder/"coming soon" content.
   */
  specifications?: SpecSection[];
  reviews?: Review[];
  ratingDistribution?: RatingBreakdown[];
  seller?: Seller;
  description?: string;
}

export type SessionEventType =
  | "view"
  | "search"
  | "cart_add"
  | "cart_remove"
  | "checkout_start"
  | "abandon";

export interface SessionEvent {
  id: string;
  type: SessionEventType;
  productId?: string;
  query?: string;
  /** ISO timestamp. */
  timestamp: string;
}
```

### Counts against `src/data/products.ts`

- **50 products total** (`id: "p-…"` occurs 50 times).
- **10 of 50 have hand-authored PDP detail data** — `specifications`, `reviews`,
  `ratingDistribution`, `seller`, and `description` are each populated on
  exactly 10 products (same 10 products carry all five fields together).
- **5 of 50 have `signals` populated** (`p-1001` and four others).
- **Important nuance:** the PDP does not actually show "thin" pages for the
  other 40 products. `ProductDetail.tsx` calls `getSpecifications`,
  `getDescription`, `getSeller`, `getRatingDistribution`, and `getReviews` from
  `src/lib/productDetails.ts`, which fall back to a **deterministic mulberry32
  PRNG seeded by product id** whenever hand-authored data is absent. So every
  one of the 50 products renders a full PDP; only 10 of them are backed by
  real authored copy, the rest are synthesized but stable across reloads.

### `src/data/session.ts`

39 lines: a static `sessionEvents: SessionEvent[]` array (19 hand-written
events forming one narrative session) and a static `cartProductIds = ["p-1001",
"p-1003", "p-3002"]` array. **This file is not imported anywhere in `src/`** —
confirmed via a repo-wide grep for its exports and its relative import path.
It appears to be leftover seed data from an earlier iteration of the demo and
is currently dead code.

---

## 3. State

Three layers, not one.

### React Context (reactive UI state, localStorage-backed)

| Context | File | localStorage key | Exports |
|---|---|---|---|
| `CartContext` | `src/context/CartContext.tsx` | `fk-cart-v1` | `CartItem`, `CartState`, `CartAction`, `cartReducer`, `CartProvider`, `useCart()` → `{ items, addItem(productId, quantity?, addedAt?), updateQuantity, removeItem, clearCart, count }`. The `addedAt` override on `addItem` exists only for the demo-scenario loader to backdate cart age. |
| `WishlistContext` | `src/context/WishlistContext.tsx` | `fk-wishlist-v1` | `WishlistState`, `WishlistAction`, `wishlistReducer`, `WishlistProvider`, `useWishlist()` → `{ productIds, has(id), toggle(id), add(id), remove(id) }`. |
| `TrackerContext` | `src/context/TrackerContext.tsx` | (delegates to `sessionTracker`, no key of its own) | Wraps `sessionTracker` in React state; exposes `recordProductVisit`, `recordSearch`, `recordPincodeCheck`, `runRootCauseAnalysis`, `buildShopperProfile()`, etc. Uses refs (`itemsRef`, `totalsRef`, `routeRef`, `wishlistRef`) to avoid stale closures in callbacks that read cart/wishlist state. |
| `InterventionContext` **(new)** | `src/context/InterventionContext.tsx` | (delegates to `fatigueBudget`/`interventionLedger`) | The **delivery layer**, sitting downstream of `TrackerContext.rootCause`. Decides whether the Phase 3 ranked plan is worth showing, at what intensity (`interventionPolicy.ts`'s `selectSurface`), and on which surface (`inline`/`ambient`/`spotlight`/`companion`) — entirely client-side and synchronous. Reports the outcome to the backend after the fact via `sendDeliveryDecision` (fire-and-forget); never blocks on the network to decide. Exposes `active`, `surface`, `intensity`, `alternatives`, `decisionReason`, `accept()`, `dismiss()`. |

Provider nesting in `src/App.tsx`: `CartProvider > WishlistProvider >
TrackerProvider`, wrapping all six routes under one `<Layout>`.

### Plain observable stores (framework-independent, subscribe/emit pattern)

| Store | File | Persisted? | Purpose |
|---|---|---|---|
| `sessionTracker` (`SessionTracker`) | `src/lib/tracker.ts` | `sessionStorage` key `fk-pipeline-session-id` only (session id for backend dedup/budget) | Collects the 22-feature abandonment vector, drives RCA requests. |
| `pageContext` (`PageContextStore`) | `src/lib/pageContext.ts` | **Not persisted** — in-memory, session-scoped only | Current product, recent visits, search history, review-dwell tracking; feeds the companion widget's proactive triggers. |
| `userHistory` (`UserHistoryStore`) | `src/lib/userHistory.ts` | `localStorage` key `fk-user-history-v1` | Recently-viewed and past-purchase product ids (max 20 recent views). |
| `pipelineTrace` (`PipelineTraceStore`) | `src/lib/pipelineTrace.ts` | **Not persisted** — in-memory ring buffer, max 25 runs | Powers the `/pipeline` console. |
| `fatigueBudget` (`FatigueBudgetStore`) **(new)** | `src/lib/fatigueBudget.ts` | `sessionStorage`, same session scope as `tracker.ts` | The delivery layer's "should we interrupt right now" state — a decaying exposure budget (half-life decay, not a hard counter) plus a terminal per-lever dismissal list. **Remains entirely client-authoritative**: this is a synchronous, sessionStorage-backed check with no server round-trip in the decision path itself. The backend never decides fatigue; `POST /api/delivery-decision` only records what the client already decided, after the fact. |
| `interventionLedger` (`InterventionLedger`) **(new)** | `src/lib/interventionLedger.ts` | `sessionStorage`, rehydrated from the backend on load | Session-scoped record of *held* (no-intervention) decisions and *suppressed* rung-3 (costly) levers — the delivery layer's audit trail, feeding the `/pipeline` ledger panel's "promotional spend avoided" figure. Unlike `fatigueBudget`, this one is **not** purely client-authoritative: on construction it fire-and-forgets a `hydrate()` call to `GET /api/session-ledger/:id`, which replaces local state with the SQLite-backed durable copy — so a fresh tab or cleared sessionStorage still shows the session's real history. sessionStorage is the fast/optimistic path; the DB is the source of truth. |
| `memory_store` (`InterventionMemoryStore`, backend) | `backend/agents/memory.py` | **SQLite-backed** (`intervention_events` table, `source` column) — was an in-process dict, migrated (see §9a) | Tracks which interventions were shown/dismissed per session, used as a repetition penalty in scoring. Survives a backend restart now; previously this reset every restart. |

### Summary of storage keys actually in use

- `localStorage`: `fk-cart-v1`, `fk-wishlist-v1`, `fk-user-history-v1`
- `sessionStorage`: `fk-pipeline-session-id`, `fk-intervention-ledger-v1` (new),
  plus `fatigueBudget.ts`'s own key
- Backend `gate_state`/`intervention_events`/`decisions` are **now SQLite-backed**
  (see §9a) and survive a restart — this supersedes the "in-memory, resets on
  restart" characterization that used to apply to `agents/gate.py` and
  `agents/memory.py`.
- Everything else (page context, pipeline trace runs) is still in-memory only and
  resets on reload or backend restart — that part of the original claim still holds.

---

## 4. Routes and Pages

All six routes are declared in `src/App.tsx`, rendered inside a shared
`<Layout>` (which itself renders `<Navbar>`, `<CategoryNav>`, the routed
`<Outlet>`, `<Footer>`, plus two always-mounted overlays: `<AgentInspector>`
and `<CompanionWidget>`).

| Route | Component | What's on the page |
|---|---|---|
| `/` | `Home.tsx` | `CategoryStrip` (icon row), `HeroCarousel` (4 auto-advancing banners), three `ProductRail`s: "Deals of the Day" (top 12 by discount %), "Best of Electronics" (category filter), "Suggested for You" (top 12 by rating — comment notes this is "the slot the agent will later personalise"). |
| `/product/:slug` | `ProductDetail.tsx` | Image gallery, title + wishlist toggle, price block, offers list, pincode-check form, seller line, highlights, specifications table, description, ratings & reviews section. Records a product visit / view / page-context update on mount. |
| `/cart` | `CartPage.tsx` | Empty-state illustration if no items, else a list of `CartLineItem`s + `PriceSummary` with a "Place Order" CTA that navigates to `/checkout`, plus a "You might also like" `ProductRail`. |
| `/checkout` | `CheckoutPage.tsx` | Redirects to `/cart` if empty. Three-step flow via local `step` state: (1) `AddressForm`, (2) read-only order summary (`CartLineItem` in `readOnly` mode) + Continue button, (3) `PaymentOptions` + Place Order button. On order placement, generates a fake `OD…` order id, records the purchase to `userHistory`, and shows `OrderConfirmation`. |
| `/search` | `SearchResultsPage.tsx` | Reads `q`, `category`, `label` query params. Filters the 50-product catalog by category and/or free-text match against title/brand/subCategory/category. Distinguishes "no matching text" from "clicked a nav category with no inventory" (Grocery, Home & Furniture, etc.) and shows a tailored empty state. |
| `/pipeline` | `PipelineConsole.tsx` | The dev-facing pipeline console: `ScenarioPicker` (6 presets), a list of recent runs, `TraceWaterfall` for the selected run's spans, and `RcaReport` (root cause + evidence + intervention plan) when a run has results. |

---

## 5. Component Inventory

One line each, grouped by directory. "Reused" = imported from more than one
route/page.

**`src/components/ui/`** (design-system primitives, all reused across ≥2 pages)
- `Badge.tsx` — `AssuredBadge`, `DiscountBadge`, `SponsoredBadge`, `PlusBadge`; small styled `<span>`s, each takes its own props (e.g. `{percent}`), no shared interface.
- `Button.tsx` — `Button({variant, size, ...ButtonHTMLAttributes})`; 6 variants (primary/login/cart/buy/ghost/outline), 2 sizes. Used everywhere.
- `PriceBlock.tsx` — `PriceBlock({mrp, sellingPrice, size?, className?})`; renders selling price, struck-through MRP, and discount % if any.
- `RatingStars.tsx` — `RatingStars({value, count?, variant?: "pill"|"stars", size?, className?})`; green pill badge on cards, 5-star row on PDP.
- `SocialIcons.tsx` — `FacebookIcon`, `TwitterIcon`, `YoutubeIcon`, `InstagramIcon`; inline SVGs (`{className?}`), used only in `Footer.tsx`.
- `AgentInspector.tsx` — floating dev-tool panel (295 lines) showing the last Phase 1 prediction + a link into `/pipeline`; no props, reads `sessionTracker`/`pipelineTrace` directly. Still titled "Phase 1 Risk Inspector" (stale — see §10).

**`src/components/layout/`**
- `Navbar.tsx` — top blue bar: logo, search form (`recordSearch` + navigate to `/search?q=`), Login dropdown, "Become a Seller" link, "More" dropdown, cart icon with live count badge. No props (reads `useCart`/`useTracker`).
- `CategoryNav.tsx` — secondary white nav strip, links built from `navCategories`; no props.
- `Footer.tsx` — full footer: 4 link columns, social icons, address blocks, bottom link bar; no props, all content hardcoded.
- `Logo.tsx` — Flipkart wordmark + "Explore Plus" kicker; no props.
- `Layout.tsx` — page shell: `Navbar` + `CategoryNav` + `<Outlet>` + `Footer` + globally-mounted `AgentInspector` + `CompanionWidget`; no props. Used by every route (via `App.tsx`).

**`src/components/home/`** (all reused between `Home` and other pages except `HeroCarousel`/`CategoryStrip`, which are Home-only)
- `HeroCarousel.tsx` — auto-advancing (5s) banner carousel over `banners` data, with prev/next buttons and dot indicators; no props.
- `CategoryStrip.tsx` — circular category icon row from `homeCategories`; no props.
- `ProductRail.tsx` — `ProductRail({title, subtitle?, products})`; horizontally-scrollable row of `ProductCard`s with a "View All" button and scroll-arrow affordances. **Reused** on `Home` and `CartPage`.
- `ProductCard.tsx` — `ProductCard({product, fixedWidth?})`; the catalog tile — image, wishlist heart, sponsored/assured badges, rating, price, delivery line. **Reused** on `Home` (via `ProductRail`), `CartPage`, `SearchResultsPage`.

**`src/components/pdp/`** (ProductDetail-only)
- `ImageGallery.tsx` — `ImageGallery({productId, images, title})`; thumbnail rail + main image, wishlist/share icon buttons, "Add to Cart" (wired) and "Buy Now" (inert — commented) buttons.
- `SpecificationsTable.tsx` — `SpecificationsTable({sections})`; grouped label/value table.
- `OffersList.tsx` — `OffersList({offers, emi?})`; classifies raw offer strings into bank/EMI/exchange/combo/special rows with expandable T&C text; synthesizes an EMI row and a fallback bank offer if none authored.
- `RatingsAndReviews.tsx` — `RatingsAndReviews({productId, ratingDistribution, reviews})`; rating breakdown bars + paginated review list; tracks one-shot visibility and a continuous 15s+ dwell timer (feeds the companion widget's proactive trigger) via `pageContext.markReviewDwell`.

**`src/components/cart/`**
- `CartLineItem.tsx` — `CartLineItem({product, quantity, readOnly?})`; quantity stepper (cart) or static qty (checkout `readOnly`), "Save for later" (inert — commented) and "Remove" (wired) actions. **Reused** on `CartPage` and `CheckoutPage`.
- `PriceSummary.tsx` — `PriceSummary({totals, action?})`; price breakdown card with an optional CTA button. **Reused** on `CartPage` and `CheckoutPage`.

**`src/components/checkout/`** (CheckoutPage-only)
- `CheckoutStepper.tsx` — `CheckoutStepper({current})`; 3-step progress indicator (Delivery Address / Order Summary / Payment).
- `AddressForm.tsx` — `AddressForm({value, onChange, onSubmit})`; also exports `Address` type, `EMPTY_ADDRESS`, `isAddressComplete()`. All 6 fields required, purely local state, nothing is sent anywhere.
- `PaymentOptions.tsx` — `PaymentOptions({value, onChange})`; also exports `PaymentMethod` type. 4 radio options (UPI/Card/Netbanking/COD), explicitly presentational only — "no card/UPI inputs behind any option, by design."
- `OrderConfirmation.tsx` — `OrderConfirmation({orderId, deliveryDate})`; success screen with a fake order id.

**`src/components/pipeline/`** (PipelineConsole-only)
- `ScenarioPicker.tsx` — renders the 6 `DEMO_SCENARIOS` as clickable cards, each showing label/intent/expected-outcome/accent color — confirms scenario type **is** visible in the UI as intended.
- `TraceWaterfall.tsx` — renders a run's `TraceSpan[]` as a latency waterfall; `STAGE_ICONS` covers every stage the backend emits, including `"intervention_ranking"` and `"critic_verdict"`.
- `RcaReport.tsx` — renders root cause, evidence (SHAP bars), shopper narrative, confidence, recommended/avoided levers, and (newer) an `InterventionPlanPanel` showing ranked interventions with score bars and agent-endorsed badges.

**`src/components/companion/`**
- `CompanionWidget.tsx` — the persistent "AI Shopping Companion" chat widget (524 lines), docked at the right edge, graduated presence (dormant/ambient/attentive), reactive Q&A plus proactive prompt-offers from behavioral heuristics (review dwell ≥15s, ≥3 pincode checks, ≥1 failed coupon, 3+ similar-product visits). No props — globally mounted in `Layout.tsx`, reads context/stores directly.

---

## 6. Shared Utilities (`src/lib/`)

| File | Exports (signature) | Returns / purpose |
|---|---|---|
| `tracker.ts` | `ABANDONMENT_FEATURE_NAMES`, `MATERIAL_FEATURE_NAMES`, `materialSignature(features)`, `SESSION_ID`, `class SessionTracker` (singleton `sessionTracker`), types `AbandonmentFeatures`, `TrackerSignals`, `ShopperHistory`, `CartSnapshot`, `ScenarioSessionState`, `ShopperProfilePayload`, `CartContextPayload`, `TrackerSnapshot`, `RiskTier`, `PredictionResponse`, `InterventionFeedbackAction` | Core telemetry engine: builds the 22-feature vector, calls `/api/predict-abandonment` and `/api/root-cause-analysis`, applies/resets demo scenarios, sends intervention feedback. |
| `pipelineTrace.ts` | `pipelineTrace` (singleton `PipelineTraceStore`), `runDurationMs(run)`, `STAGE_LABELS`, types `PipelineStage`, `TraceSpan`, `PipelineRun`, `RootCauseResponse`, `InterventionPlan`, `RecommendedIntervention`, `ExplanationFactor` | Client-side ring buffer (max 25) of pipeline runs for `/pipeline`; merges backend spans with a frontend telemetry span. |
| `pageContext.ts` | `pageContext` (singleton `PageContextStore`), `findComparisonCandidates(history): ProductVisit[] \| null`, types `ProductVisit`, `PageContextSnapshot` | In-memory (unpersisted) tracking of current product, visit history, search history, review-dwell state — feeds companion widget triggers. |
| `userHistory.ts` | `userHistory` (singleton `UserHistoryStore`), `recordView(id)`, `recordPurchase(ids[])`, type `UserHistorySnapshot` | localStorage-persisted recent-views (max 20) and past-purchases list. |
| `companionChat.ts` | `buildProductContext(product): ProductContextPayload`, `sendCompanionChatMessage(productContext, messages, comparisonProducts?, searchHistory?): Promise<CompanionChatResponse>` | Assembles product context and POSTs to `http://localhost:8000/api/companion-chat`. |
| `cartTotals.ts` | `computeCartTotals(items): CartTotals`, constants `FREE_DELIVERY_THRESHOLD=500`, `DELIVERY_CHARGE=40` | MRP total, discount, delivery charge, free-delivery flag, grand total, savings. |
| `format.ts` | `formatINR(n)`, `formatIndianNumber(n)`, `discountPercent(mrp, sellingPrice)`, `formatDeliveryDate(days)` | Currency/number/date formatting helpers used throughout the UI. |
| `productDetails.ts` | `getSpecifications(product)`, `getDescription(product)`, `getSeller(product)`, `getRatingDistribution(product)`, `getReviews(product)` (plus internal mulberry32 PRNG helpers) | Deterministic per-product-id fallback generator for PDP detail fields when hand-authored data is absent (39 of 50 products rely on this for some/all fields). |

---

## 7. Instrumentation Hooks

**This is the section the user flagged as mattering most — it's where the
agent layer attaches.**

### `data-testid` attributes (23 total, all in `src/`)

| testid | File |
|---|---|
| `cart-badge` | `Navbar.tsx` |
| `add-to-cart-button` | `ImageGallery.tsx` |
| `buy-now-button` | `ImageGallery.tsx` (button is inert — see §8) |
| `cart-item` | `CartLineItem.tsx` |
| `cart-item-quantity` (×2, stepper + readOnly variants) | `CartLineItem.tsx` |
| `cart-item-remove` | `CartLineItem.tsx` |
| `cart-total-amount` | `PriceSummary.tsx` |
| `{action.testId}` (dynamic — resolves to `place-order-button` from `CartPage.tsx`) | `PriceSummary.tsx` |
| `reviews-section` | `RatingsAndReviews.tsx` |
| `show-more-reviews-button` | `RatingsAndReviews.tsx` |
| `address-form` | `AddressForm.tsx` |
| `save-address-button` | `AddressForm.tsx` |
| `checkout-stepper` | `CheckoutStepper.tsx` |
| `order-confirmation` | `OrderConfirmation.tsx` |
| `order-id` | `OrderConfirmation.tsx` |
| `payment-options` | `PaymentOptions.tsx` |
| `order-summary` | `CheckoutPage.tsx` |
| `continue-to-payment-button` | `CheckoutPage.tsx` |
| `edit-order-summary` | `CheckoutPage.tsx` |
| `confirm-order-button` | `CheckoutPage.tsx` |
| `edit-address` | `CheckoutPage.tsx` |
| `cart-empty` | `CartPage.tsx` |

Coverage is concentrated in cart/checkout. **No `data-testid`s exist on**: the
Navbar search input/button, wishlist toggle buttons, category nav links, home
page rails/carousel, the pipeline console, or the companion widget.

### Forward-looking markers

Exactly **one** explicit `TODO(agent)` marker exists in the codebase, in
`src/routes/CheckoutPage.tsx:63-64`:

```ts
// TODO(agent): fire an "order_completed" SessionEvent here so the
// cart-abandonment model can distinguish converted carts from abandoned ones.
```

This is real and unaddressed: `placeOrder()` calls `userHistory.recordPurchase(...)`
and `clearCart()`, but never emits a `SessionEvent` of type `"abandon"`'s
counterpart. Combined with `src/data/session.ts` being unused (§2), there is
currently **no mechanism anywhere in the app that distinguishes a completed
purchase from an abandoned session** for training/labeling purposes — the ML
pipeline is trained entirely on the synthetic generator, not on live app
telemetry.

No other `TODO`/`FIXME`/"agent layer"/"integration point" comments exist in
`src/` or `backend/` beyond this one and the doc-level design commentary in
`backend/agents/README.md`.

### Non-testid integration surfaces worth knowing about

- `ProductSignals.abandonmentScore` field exists on the `Product` type
  (§2) but nothing currently writes to it — it's a typed extension point, not
  a wired one.
- `pageContext` and `userHistory` are the two stores explicitly built as
  framework-independent so they're readable outside React — i.e., they're the
  intended attachment points for anything that needs shopper state without a
  hook.

---

## 8. What's Inert

Exhaustive, by control:

| Control | Location | Status |
|---|---|---|
| **Buy Now** | `ImageGallery.tsx` (PDP) | **Inert — no `onClick` at all.** Explicit code comment: `/* Buy Now stays inert until the checkout flow lands. */` (checkout now exists; the button was never wired to it). Has `data-testid="buy-now-button"`. |
| **Save for later** | `CartLineItem.tsx` (cart page only) | **Inert — no `onClick` at all.** Explicit comment: "there's no saved-items store yet and faking one would be misleading." No testid. |
| **Wishlist heart on `ImageGallery`** (top-right of main product image) | `ImageGallery.tsx` | **Inert — no `onClick`, `aria-label="Add to wishlist"` but does nothing.** This is a *separate, duplicate* wishlist button from the one in `ProductDetail.tsx`'s header, which **is** fully wired to `WishlistContext`. |
| **Share icon** | `ImageGallery.tsx` | **Inert — no `onClick` at all.** `aria-label="Share"`, purely decorative. |
| **Pincode check** | `ProductDetail.tsx` | **Stub, not inert.** The form submits and calls `recordPincodeCheck(pincode)` — this is real telemetry (feeds the abandonment feature vector and the companion widget's "3+ pincode checks" trigger) — but there is no actual serviceability/ETA lookup; the delivery estimate shown is static, unaffected by the pincode entered. |
| **Search bar** | `Navbar.tsx` | **Fully wired**, not inert. Submits, calls `recordSearch`, `pageContext.recordSearch`, and navigates to `/search?q=...`, which performs a real client-side filter against the 50-product catalog. |
| **Category nav links** (`CategoryNav.tsx`, `CategoryStrip.tsx`) | Layout / Home | **Wired, but honestly limited.** Every link navigates to `/search?category=…`. For categories with a real `categorySlug` (Mobiles, Fashion, Electronics, Appliances, Audio) this filters real inventory. For categories with `categorySlug: null` (Grocery, Home & Furniture, Flight Bookings, Beauty/Toys, Two Wheelers) it navigates to a `/search` page that correctly renders an honest "we don't carry this category yet" empty state rather than faking results. This is intentional, not broken. |
| **"Become a Seller"** (Navbar and Footer) | `Navbar.tsx`, `Footer.tsx` | **Inert** — `<Link to="#">`, no handler. |
| **"More" dropdown items** (Notification Preferences, 24x7 Customer Care, Advertise, Download App) | `Navbar.tsx` | **Inert** — plain `<button>`s with no `onClick`. |
| **Account dropdown items** (My Profile, Flipkart Plus Zone, Orders, Wishlist, Rewards, Gift Cards) | `Navbar.tsx` | **Inert** — plain `<button>`s with no `onClick`. Note the "Wishlist" entry here does **not** link to the real, working `WishlistContext` — it's decorative. |
| **Login button** | `Navbar.tsx` | **Inert as an action** — only opens/reveals the (also inert) account dropdown on hover; there is no auth system in this app at all (`AddressForm`/`isGuestCheckout` assumptions confirm the app models every shopper as a guest). |
| **All footer links** (About/Group Companies/Help/Consumer Policy columns, Social icons, bottom bar: Become a Seller/Advertise/Gift Cards/Help Center) | `Footer.tsx` | **Inert** — every one is `<Link to="#">`, purely decorative. |
| **"View All" button** on every product rail | `ProductRail.tsx` | **Inert — no `onClick` at all.** |
| **Payment method radio buttons** | `PaymentOptions.tsx` | **Wired for selection state**, but by design collect nothing — explicit comment: "no card/UPI inputs behind any option... nothing here collects or transmits payment details." Selecting a method just changes local state; "Place Order" proceeds regardless of which is chosen. |

Everything else that looks like a button/link and isn't listed above (Add to
Cart, cart quantity stepper, Remove, wishlist toggles on `ProductCard` and
`ProductDetail`, checkout step navigation, Place Order / Confirm Order,
carousel prev/next/dots, rail scroll arrows, offer T&C expanders, review
pagination) is genuinely wired to real state changes.

---

## 9. Backend State

The Python/FastAPI backend **exists and is substantially built** — this is not
a stub.

### Routes (`backend/main.py`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/metrics` | Exposes model metrics (from `ml/artifacts/metrics.json`) |
| POST | `/api/predict-abandonment` | Phase 1: 22-feature vector → XGBoost probability + SHAP impacts |
| GET | `/api/pipeline-config` | Config the frontend needs (thresholds etc.) |
| POST | `/api/root-cause-analysis` | Phase 2: runs prediction + gate + (if fired) Groq RCA + Phase-3 intervention ranking, all as one traced pipeline run |
| POST | `/api/intervention-feedback` | Records accept/dismiss/convert feedback into `memory_store`; also annotates the matching `intervention_events` row with delivery context (rung/surface/root cause) via `ledger.annotate_latest_event` |
| POST | `/api/delivery-decision` **(new)** | Delivery layer's write path — one call per pipeline run reporting what `InterventionContext.tsx` decided (deliver-or-hold), plus any suppressed rung-3 levers. The decision itself is made client-side beforehand; this only records it (see §9a). |
| GET | `/api/session-ledger/{session_id}` **(new)** | Rebuilds `SessionLedgerResponse` (shown-by-rung, accepted/dismissed/ignored, held decisions, suppressed rung-3 levers, spend avoided) from `intervention_events` + `decisions`. Returns an empty-but-valid ledger for an unknown session rather than 404. |
| POST | `/api/companion-chat` | Companion widget's reactive Q&A endpoint |

### 9a. Persistence layer (`backend/db.py`, `backend/ledger.py`) — new

Previously, `agents/gate.py`'s `GateStore` and `agents/memory.py`'s
`InterventionMemoryStore` were process-local Python dicts, called out in Known
Issues (§10, item 12) as not surviving a restart. **That is now only half true.**
`backend/db.py` adds a stdlib-`sqlite3` (no ORM) persistence layer at
`backend/data/app.db` (WAL mode, one connection per thread via `threading.local()`,
gitignored — `backend/data/` exists as a directory with a `.gitkeep` but the `.db`
file itself is never committed), and both stores now read/write through it. A
backend restart no longer resets RCA cooldowns, the per-session analysis cap, or the
repetition-penalty history. `pageContext`/`userHistory`/`pipelineTrace` (frontend,
in-memory) and `pipelineTrace`-style backend state are unaffected — the migration
was scoped to gate/memory only.

Five tables (`backend/db.py`'s `SCHEMA`):

| Table | Purpose |
|---|---|
| `sessions` | One row per session id, touched (`db.touch_session`) by every other write path — a complete list of sessions the other tables reference, without a foreign-key ordering constraint. |
| `gate_state` | One row per session; mirrors the old in-memory `SessionState` field-for-field (`fire_count`, `root_cause_signature`, `last_fired_at`). Backs `GateStore`. |
| `intervention_events` | **Append-only.** One row per lever-related event — ranking exposure, shopper feedback, delivered render, or suppressed rung-3 lever. See the `source` column below; this is the table both `memory_store`'s repetition penalty and `ledger.py`'s session-ledger read from. |
| `decisions` | One row per pipeline run's delivery verdict — `intervene` or `do_nothing`. "Do nothing" is recorded exactly like "intervene": an absent row would be indistinguishable from a run that never happened, so every run writes one. |
| `reservations` | Written by `backend/reservations.py`. When a run clears the RCA threshold **and** diagnoses `cost_friction` or `product_uncertainty`, one unit of the cart's highest-value in-stock line is held for 10 minutes (`HOLD_SECONDS`). Released early by `POST /api/cart-add` (the shopper committed, so the cart is the claim now) or left to lapse — expiry is evaluated at read time in `active_count`, so there is no sweeper. `GET /api/product-availability/{id}?quantity_left=N` returns `N` minus the active holds; `quantity_left` is supplied by the caller because the catalog lives in `src/data/products.ts` and a server-side copy would be a second thing to keep in step. A session never stacks holds on the same product — the gate allows 10 analyses per session, and one hesitating shopper is still one unit of demand. Nothing customer-facing announces any of this. |

**The `intervention_events.source` column** (`ranked` / `delivered` / `suppressed`,
`CHECK`-constrained) is what stops the ledger from triple-counting. Three different
things all used to plausibly be called "shown":

- `source='ranked'` — the top-3 (or top-N) levers `agents/intervention.py`'s
  ranking actually scored for a run. This is what `InterventionMemoryStore.get()`
  reads for the repetition penalty — it deliberately excludes `'delivered'` rows
  (see next) so a lever that was ranked-and-shown-to-the-shopper isn't counted twice
  toward its own penalty.
- `source='delivered'` — the *one* lever `InterventionContext.tsx` actually rendered
  on screen, written by `ledger.record_decision` when `outcome == "delivered"`. This
  is the only `source` the ledger's `shownByRung`/`spendAvoided`-adjacent counts read
  for "what did the shopper actually see."
- `source='suppressed'` — rung-3 (margin-spending) levers the ranking offered that
  policy (`interventionPolicy.ts`'s `findSuppressedRung3Levers`) withheld, whether or
  not something else was delivered instead. Feeds the ledger's "promotional spend
  avoided" total via `RUNG3_ASSUMED_VALUE_INR` (duplicated — deliberately — between
  `backend/agents/levers.py` and `src/lib/interventionPolicy.ts`; `tests/test_persistence.py`
  pins the Python side).

Without this column, summing "shown" across ranking exposure, actual render, and
policy-suppressed-but-considered would overstate every ledger metric derived from
it. `build_session_ledger` in `backend/ledger.py` is the one place all three get
read back out and reassembled into the shape `InterventionLedgerPanel` (frontend)
renders.

**What stays client-authoritative vs. what the DB now owns:** the *decision* of
whether to interrupt the shopper right now (fatigue budget, intensity ladder,
surface selection) is still made entirely in the browser —
`src/lib/fatigueBudget.ts` is sessionStorage-backed and synchronous, with no server
round-trip in the decision path itself, exactly as before this migration. What
changed is that the *record* of what was decided is no longer sessionStorage-only:
`InterventionContext.tsx` fire-and-forgets that record to
`POST /api/delivery-decision` after deciding, and `interventionLedger.ts` rehydrates
from `GET /api/session-ledger/:id` on load so a fresh tab or cleared storage still
shows the session's real history. The backend is a durable mirror of a client
decision, not a participant in making it.

### Dataset and training — has this actually been run?

**Yes.** `ml/data/cart_abandonment_dataset.csv` exists on disk with 200,000
rows (200,001 lines including header), matching `metrics.json`'s
`train_rows(120000) + calibration_rows(40000) + test_rows(40000) = 200000`.
All four model artifacts are present and non-empty: `model.joblib` (1.46 MB),
`explainer.joblib` (4.89 MB), `feature_names.json`. **One artifact is
suspicious**: `calibrator.joblib` is only **4 bytes** on disk — effectively an
empty/placeholder file — and `metrics.json` explicitly confirms
`"isotonic_calibration_applied": false`. So while the code path for isotonic
calibration exists (`backend/config.py`, `ml/train_model.py`), it is **not
currently active**; the model in production is the raw uncalibrated XGBoost
output. This matches the `log_loss` and `log_loss_uncalibrated` fields in
`metrics.json` being identical.

### Current model performance (`ml/artifacts/metrics.json`)

- ROC-AUC: **0.8071** (95% CI 0.8036–0.8117), **99.56% of the Bayes-optimal
  ceiling** (`auc_efficiency_vs_bayes: 0.9956`) computed against the
  generator's known ground-truth probabilities.
- PR-AUC 0.8958, accuracy 0.761, F1 0.834, Brier 0.161, ECE 0.0076.
- 32 engineered features, best iteration 253.
- At the RCA trigger threshold (probability ≥ 0.80): 40.3% coverage, 90.4%
  precision, 1.33x lift over base rate — this is the number the RCA gate
  policy is justified against in `backend/agents/README.md`.

These are **synthetic-data metrics only** — `ml/generate_dataset.py` produces
probabilistically-labeled synthetic sessions; nothing here has been validated
against real user behavior, and the README explicitly warns against
representing these as production performance.

### The RCA agent (Phase 2) — Groq, `openai/gpt-oss-120b`

Fires only when probability ≥ 0.80 AND cart age ≥ 10s AND (feature signature
changed OR 90s cooldown elapsed) AND session hasn't hit its 10-analysis cap.
Uses strict `json_schema` mode specifically because it was benchmarked against
alternatives (llama-3.3-70b, qwen3.6-27b, gpt-oss-20b) and was the only model
that guaranteed schema conformance — documented with real benchmark numbers in
`backend/agents/README.md`. Known documented limitation: the free Groq tier
(12k tokens/min) means clicking through all 6 demo scenarios back-to-back
**will** hit rate limits; the README recommends ~20s between scenarios.

### The intervention ranking (Phase 3) and companion chat — built, not just planned

Contrary to what an earlier phase of this project may have implied, this is
**not** still "out of scope." `backend/agents/intervention.py` (deterministic
weighted scoring over 14 levers in `levers.py`) and
`backend/agents/companion_chat.py` (a second, independently-configured Groq
call for the persistent chat widget) both exist and are wired into
`/api/root-cause-analysis` and `/api/companion-chat` respectively.

### Tests (`tests/`)

Four files: `test_phase1_pipeline.py`, `test_rca_agent.py`,
`test_companion_chat.py`, `test_intervention_agent.py`. `backend/agents/README.md`
states 33 RCA tests + 12 Phase 1 tests pass; the companion/intervention test
files exist but their pass status was not re-verified as part of this
read-only audit (no test run was executed). **`package.json` has no `"test"`
script** — the only documented way to run anything is
`python -m unittest discover -s tests -v` per the root `README.md`.

---

## 10. Known Issues

Ranked roughly by how much they'd surprise someone designing the next phase:

1. **Root README.md is stale and describes the wrong repo layout.** It refers
   to a nested `Flipkart-grid-8.0/` frontend directory and
   `npm --prefix Flipkart-grid-8.0 run dev`, neither of which match the actual
   single-repo layout (`src/` at root, run with plain `npm run dev`). It also
   only documents Phase 1 (`/api/predict-abandonment`) and doesn't mention
   `/api/root-cause-analysis`, `/api/companion-chat`, `/api/intervention-feedback`,
   or the `/pipeline` console at all. Anyone onboarding from the README alone
   would materially misunderstand both the structure and the current feature
   set.

2. **`src/data/session.ts` is dead code.** Its exports (`sessionEvents`,
   `cartProductIds`) are not imported anywhere in `src/`. Either it's a
   leftover from an earlier prototype, or it was meant to seed something that
   never got wired up.

3. **The one explicit `TODO(agent)` is real and unresolved**
   (`CheckoutPage.tsx:63`): order completion never emits a distinguishing
   `SessionEvent`, so there is currently no first-party signal anywhere that
   separates a converted session from an abandoned one — the model is trained
   purely on synthetic data, and live app usage doesn't currently feed
   anything back into it.

4. **Isotonic calibration is built but inactive.** `calibrator.joblib` is a
   4-byte placeholder and `metrics.json` confirms
   `isotonic_calibration_applied: false`. The raw XGBoost probabilities are
   what's actually served; this may or may not be intentional, but it
   contradicts the calibration infrastructure that exists in `ml/train_model.py`
   and `backend/config.py`.

5. **Two independent, inconsistent wishlist buttons on the PDP.** The one in
   `ProductDetail.tsx`'s header is fully wired to `WishlistContext`; the
   visually similar heart icon inside `ImageGallery.tsx` (top-right of the
   main image) has no handler at all. A user could reasonably click either
   expecting the same result.

6. **`Buy Now` was never revisited after checkout was built.** The inline
   comment ("stays inert until the checkout flow lands") is now stale —
   `/checkout` exists and works — but the button was never connected to it.

7. **Minor naming/label staleness from the Phase 2 → Phase 3 transition:**
   - `AgentInspector.tsx` is still titled "Phase 1 Risk Inspector" despite now
     linking into the full multi-stage `/pipeline` console.
   - `PipelineConsole.tsx`'s header subtitle doesn't mention the newer
     "intervention ranking" stage even though it renders in every completed
     run's trace and report.
   - *(Resolved: `TraceWaterfall.tsx`'s `STAGE_ICONS` now covers
     `"intervention_ranking"` and `"critic_verdict"`.)*

8. **`data-testid` coverage is uneven.** Cart and checkout are well covered;
   the Navbar (search, wishlist, cart badge is the only exception), category
   nav, home page rails/carousel, the `/pipeline` console, and the companion
   widget have none. Anything that automates or tests against those surfaces
   currently has to fall back to text/role selectors.

9. **No frontend test suite and no `npm test` script.** All automated tests
   are Python (`tests/`, run via `python -m unittest discover`). There is no
   verification of `src/` beyond `tsc -b` at build time and manual browser
   checking.

10. **Console errors mentioned in earlier review passes.** A prior review of
    this app flagged intermittent `Facebook`/lucide-react-related console
    errors as stale/cached browser noise rather than a live application bug.
    This audit is read-only and did not start the dev server to re-observe
    the live console, so that determination is carried forward, not
    re-verified — if it resurfaces, re-check it directly rather than trusting
    this note indefinitely. Separately, a static grep of `src/` for
    `console.error`/`console.warn` calls in application code found **none**,
    so if a console error is currently visible it is not something the app
    code is deliberately logging.

11. **Pincode check is telemetry-only, not a real lookup**, and payment
    method selection collects nothing — both are intentional simplifications
    (documented in-code), not bugs, but worth knowing before assuming either
    could support a real serviceability or payment feature without further
    backend work.

12. **Resolved since the original pass: `GateStore` and `InterventionMemoryStore`
    are no longer process-local in-memory dicts.** `backend/db.py` /
    `backend/ledger.py` (see §9a) migrated both onto SQLite (`backend/data/app.db`),
    so a backend restart no longer loses RCA dedup/budget state or intervention
    feedback history. What's still true: this is a **single-file SQLite DB**, so it
    does not solve multi-instance deployment (still fine for a single-process demo,
    not for anything resembling horizontally-scaled production). The
    `reservations` table is now read and written (§9a).

13. **A Gemini API key was pasted into a chat session during this project's
    development** (unrelated to code in this repo) and was not committed
    anywhere — it should be rotated if it hasn't been already. No Gemini
    integration exists in this codebase; the only LLM provider wired in
    anywhere is Groq (`GROQ_API_KEY` / `COMPANION_GROQ_API_KEY` in
    `backend/config.py`).
