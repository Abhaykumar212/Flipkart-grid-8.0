import type { SessionEvent } from "../types/product";

/**
 * Seed telemetry for the cart-abandonment agent.
 *
 * Reads as one plausible browsing session ending in an abandoned cart: the user
 * searched, compared two phones and a TV, added three items, removed one, opened
 * checkout, then dropped off. Timestamps line up with the `signals` blocks in
 * `products.ts`.
 */
export const sessionEvents: SessionEvent[] = [
  { id: "e-01", type: "search", query: "iphone 16", timestamp: "2026-07-31T19:38:04+05:30" },
  { id: "e-02", type: "view", productId: "p-1001", timestamp: "2026-07-31T19:39:10+05:30" },
  { id: "e-03", type: "view", productId: "p-1002", timestamp: "2026-07-31T19:41:22+05:30" },
  { id: "e-04", type: "view", productId: "p-1001", timestamp: "2026-07-31T19:42:00+05:30" },
  { id: "e-05", type: "cart_add", productId: "p-1001", timestamp: "2026-07-31T19:47:12+05:30" },

  { id: "e-06", type: "search", query: "samsung galaxy s24", timestamp: "2026-07-30T20:55:31+05:30" },
  { id: "e-07", type: "view", productId: "p-1003", timestamp: "2026-07-30T20:58:12+05:30" },
  { id: "e-08", type: "cart_add", productId: "p-1003", timestamp: "2026-07-30T21:03:44+05:30" },

  { id: "e-09", type: "search", query: "boat airdopes", timestamp: "2026-07-28T13:28:40+05:30" },
  { id: "e-10", type: "view", productId: "p-4002", timestamp: "2026-07-28T13:30:00+05:30" },
  { id: "e-11", type: "cart_add", productId: "p-4002", timestamp: "2026-07-28T13:33:02+05:30" },
  { id: "e-12", type: "cart_remove", productId: "p-4002", timestamp: "2026-07-28T13:51:47+05:30" },

  { id: "e-13", type: "search", query: "gaming laptop rtx", timestamp: "2026-07-29T22:04:18+05:30" },
  { id: "e-14", type: "view", productId: "p-2001", timestamp: "2026-07-29T22:10:00+05:30" },

  { id: "e-15", type: "search", query: "43 inch smart tv", timestamp: "2026-08-01T07:58:12+05:30" },
  { id: "e-16", type: "view", productId: "p-3002", timestamp: "2026-08-01T08:02:00+05:30" },
  { id: "e-17", type: "cart_add", productId: "p-3002", timestamp: "2026-08-01T08:05:31+05:30" },
  { id: "e-18", type: "checkout_start", timestamp: "2026-08-01T08:09:55+05:30" },
  { id: "e-19", type: "abandon", timestamp: "2026-08-01T08:12:40+05:30" },
];

/** Product ids currently sitting in the abandoned cart. */
export const cartProductIds = ["p-1001", "p-1003", "p-3002"];
