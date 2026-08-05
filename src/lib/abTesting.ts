/**
 * A/B testing framework — client side. Fetches this session's experiment arm
 * once from `GET /api/ab-variant/{session_id}` (backend/ab_testing.py, which
 * assigns deterministically from a hash of the session id and persists it),
 * caches it in sessionStorage so a reload doesn't re-fetch or — worse — risk
 * landing in a different arm mid-session.
 *
 * Variant 'a' (control) is the existing fatigue-budget delivery policy,
 * untouched. Variant 'b' (treatment) bypasses the fatigue-budget hold in
 * `interventionPolicy.ts`'s `selectSurface` — see `AB_VARIANT`'s call site
 * there — so the experiment actually changes delivery behaviour, not just a
 * label attached to identical behaviour.
 */

const STORAGE_KEY = "fk-ab-variant-v1";

export type Variant = "a" | "b";

let cached: Variant | null = readCached();
let loading: Promise<Variant> | null = null;

function readCached(): Variant | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw === "a" || raw === "b" ? raw : null;
  } catch {
    return null;
  }
}

/** Synchronous read — null until `ensureLoaded` resolves at least once. */
export function getVariant(): Variant | null {
  return cached;
}

export function ensureLoaded(sessionId: string): Promise<Variant> {
  if (cached) return Promise.resolve(cached);
  if (loading) return loading;

  loading = fetch(`http://localhost:8000/api/ab-variant/${sessionId}`)
    .then((r) => r.json())
    .then((data) => {
      const variant: Variant = data.variant === "b" ? "b" : "a";
      cached = variant;
      try {
        sessionStorage.setItem(STORAGE_KEY, variant);
      } catch {
        // Non-fatal — falls back to re-fetching (and landing on the same
        // deterministic arm, since assignment is a pure hash) next time.
      }
      return variant;
    })
    .catch(() => "a" as Variant); // control on any failure — never blocks delivery

  return loading;
}
