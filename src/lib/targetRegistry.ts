/**
 * Registry of on-page DOM anchors, keyed by string id (`"pdp-delivery"`,
 * `"cart-price-block"`, ...).
 *
 * The intervention layer needs to know, for a given lever, whether the page
 * element it wants to attach to actually exists right now — without reaching
 * into the DOM from outside via querySelector/testid, which would couple the
 * intervention layer to markup it doesn't own. Instead, the component that
 * owns a given anchor point registers its own element here (via
 * `useTargetAnchor`), and the intervention layer only ever reads through this
 * registry.
 *
 * Multiple elements can register under the same key (e.g. every `CartLineItem`
 * registers its own delivery line under `cart-delivery-estimate`) — `getTarget`
 * returns the first one currently mounted, in registration order.
 */

import { useCallback, useRef } from "react";

const targets = new Map<string, HTMLElement[]>();

export function registerTarget(key: string, el: HTMLElement): () => void {
  const existing = targets.get(key) ?? [];
  targets.set(key, [...existing, el]);
  return () => unregisterTarget(key, el);
}

export function unregisterTarget(key: string, el: HTMLElement): void {
  const existing = targets.get(key);
  if (!existing) return;
  const next = existing.filter((candidate) => candidate !== el);
  if (next.length > 0) targets.set(key, next);
  else targets.delete(key);
}

/** First currently-mounted element registered under `key`, if any. */
export function getTarget(key: string): HTMLElement | null {
  return targets.get(key)?.[0] ?? null;
}

/** First currently-mounted element across an ordered list of candidate keys. */
export function getAllMounted(keys: string[]): HTMLElement | null {
  for (const key of keys) {
    const el = getTarget(key);
    if (el) return el;
  }
  return null;
}

/**
 * Ref callback for the component that owns an anchor point. Attach directly to
 * the existing JSX element — no wrapper node needed:
 *
 *   <p ref={useTargetAnchor("pdp-delivery")}>...</p>
 *
 * Registers on mount, unregisters on unmount, independent of whether anything
 * is currently targeting this key — presence in the registry only means "this
 * anchor point exists on the page right now".
 */
export function useTargetAnchor(key: string): (el: HTMLElement | null) => void {
  const unregister = useRef<(() => void) | null>(null);

  return useCallback(
    (el: HTMLElement | null) => {
      unregister.current?.();
      unregister.current = el ? registerTarget(key, el) : null;
    },
    [key],
  );
}
