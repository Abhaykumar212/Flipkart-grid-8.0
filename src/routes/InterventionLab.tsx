import { useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { IntelligenceGlow } from "../components/intervention/IntelligenceGlow";
import { InlineHighlight } from "../components/intervention/InlineHighlight";
import { AmbientCard } from "../components/intervention/AmbientCard";
import { Spotlight } from "../components/intervention/Spotlight";
import { MotionPreferenceProvider } from "../components/intervention/useReducedMotion";

type SpotlightTarget = "center" | "edge" | null;

/**
 * Scratch route for reviewing the intervention visual primitives in
 * isolation. Nothing here reads from InterventionContext, fatigueBudget, or
 * interventionPolicy — every sample below is hardcoded. Not linked from any
 * nav; visit /intervention-lab directly.
 */
export default function InterventionLab() {
  const [reducedMotion, setReducedMotion] = useState(false);
  const [inlineActive, setInlineActive] = useState(true);
  const [showAmbient, setShowAmbient] = useState(true);
  const [ambientKey, setAmbientKey] = useState(0);
  const [spotlightTarget, setSpotlightTarget] = useState<SpotlightTarget>(null);

  const centerTargetRef = useRef<HTMLDivElement>(null);
  const edgeTargetRef = useRef<HTMLDivElement>(null);

  return (
    <MotionPreferenceProvider reduced={reducedMotion}>
      <div className="flex flex-col gap-10 pb-40">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-fk-border pb-4">
          <div>
            <h1 className="flex items-center gap-2 text-fk-xl font-semibold text-fk-ink">
              <Sparkles className="h-5 w-5 text-fk-blue" />
              Intervention Lab
            </h1>
            <p className="mt-1 text-fk-sm text-fk-muted">
              Design-only preview of the intervention visual primitives. Nothing here is wired to real pages.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setReducedMotion((v) => !v)}
            className="rounded-full border border-fk-border bg-white px-4 py-2 text-fk-sm font-medium text-fk-ink transition hover:bg-fk-bg"
          >
            Motion: {reducedMotion ? "Reduced (static glow)" : "Full animation"}
          </button>
        </header>

        <section className="flex flex-col gap-3">
          <h2 className="text-fk-md font-semibold text-fk-ink">IntelligenceGlow — bare chrome</h2>
          <p className="text-fk-sm text-fk-muted">The shared animated gradient border, at both intensities.</p>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <IntelligenceGlow intensity="subtle" rounded="rounded-2xl">
              <div className="flex h-28 items-center justify-center rounded-2xl bg-white text-fk-sm text-fk-muted">
                intensity=&quot;subtle&quot;
              </div>
            </IntelligenceGlow>
            <IntelligenceGlow intensity="present" rounded="rounded-2xl">
              <div className="flex h-28 items-center justify-center rounded-2xl bg-white text-fk-sm text-fk-muted">
                intensity=&quot;present&quot;
              </div>
            </IntelligenceGlow>
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-fk-md font-semibold text-fk-ink">InlineHighlight — rung 0</h2>
          <p className="text-fk-sm text-fk-muted">
            Wraps an existing page element. Toggle it to confirm the glow pulse never shifts the layout around it.
          </p>
          <div className="rounded-xl border border-fk-border bg-white p-5">
            <div className="flex items-center gap-2 text-fk-lg font-semibold text-fk-ink">
              <span>Price:</span>
              <InlineHighlight
                active={inlineActive}
                title="Price drop highlight"
                body="Price dropped 8% in the last 3 hours."
                actionLabel="See history"
                onAction={() => console.log("[lab] inline action")}
                onDismiss={() => setInlineActive(false)}
                reasonText="Price dropped 8% — shown because you viewed this item twice."
              >
                <span className="rounded-md bg-fk-bg px-2 py-1">₹24,999</span>
              </InlineHighlight>
            </div>
            <p className="mt-3 text-fk-sm text-fk-ink/70">Free delivery by Thu, Aug 6 · 4.3★ (12,204 ratings)</p>
          </div>
          <div>
            <button
              type="button"
              onClick={() => setInlineActive((v) => !v)}
              className="rounded-full border border-fk-border bg-white px-4 py-2 text-fk-sm font-medium text-fk-ink transition hover:bg-fk-bg"
            >
              Toggle inline highlight ({inlineActive ? "on" : "off"})
            </button>
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-fk-md font-semibold text-fk-ink">AmbientCard — rung 1</h2>
          <p className="text-fk-sm text-fk-muted">
            Docks bottom-right, above AgentInspector&apos;s debug pill. Slides in, auto-fades after ~12s.
          </p>
          <div>
            <button
              type="button"
              onClick={() => {
                setAmbientKey((k) => k + 1);
                setShowAmbient(true);
              }}
              className="rounded-full border border-fk-border bg-white px-4 py-2 text-fk-sm font-medium text-fk-ink transition hover:bg-fk-bg"
            >
              {showAmbient ? "Replay ambient card" : "Show ambient card"}
            </button>
          </div>
          {showAmbient && (
            <AmbientCard
              key={ambientKey}
              title="Save ₹450 with a bundle"
              body="Adding the matching case and screen guard qualifies this order for a 12% bundle discount."
              actionLabel="View bundle"
              onAction={() => console.log("[lab] ambient action")}
              onDismiss={() => setShowAmbient(false)}
              reasonText="Shown because similar shoppers who bundled these items returned this product 30% less."
            />
          )}
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-fk-md font-semibold text-fk-ink">Spotlight — rung 2</h2>
          <p className="text-fk-sm text-fk-muted">
            Dims the page, glows one target, anchors a callout beside it — including a target pinned near a
            viewport edge, to confirm the callout repositions instead of clipping.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setSpotlightTarget("center")}
              className="rounded-full border border-fk-border bg-white px-4 py-2 text-fk-sm font-medium text-fk-ink transition hover:bg-fk-bg"
            >
              Spotlight the centered element
            </button>
            <button
              type="button"
              onClick={() => setSpotlightTarget("edge")}
              className="rounded-full border border-fk-border bg-white px-4 py-2 text-fk-sm font-medium text-fk-ink transition hover:bg-fk-bg"
            >
              Spotlight the edge-pinned element
            </button>
          </div>

          <div ref={centerTargetRef} className="mt-2 max-w-sm rounded-xl border border-fk-border bg-white p-4">
            <p className="text-fk-sm font-semibold text-fk-ink">EMI options</p>
            <p className="mt-1 text-fk-sm text-fk-ink/70">From ₹2,083/month with No Cost EMI</p>
          </div>
        </section>

        <div
          ref={edgeTargetRef}
          className="fixed right-24 top-4 z-[20] rounded-full border border-fk-border bg-white px-3 py-1.5 text-fk-xs font-medium text-fk-ink shadow-fk-card"
        >
          Free assembly included
        </div>

        {spotlightTarget === "center" && (
          <Spotlight
            targetRef={centerTargetRef}
            title="No Cost EMI available"
            body="Split this into 12 easy instalments with zero extra interest, using an eligible bank card."
            actionLabel="View EMI plans"
            onAction={() => console.log("[lab] spotlight action")}
            onDismiss={() => setSpotlightTarget(null)}
            reasonText="Shown because this order qualifies for No Cost EMI and you've opened the EMI calculator before."
          />
        )}
        {spotlightTarget === "edge" && (
          <Spotlight
            targetRef={edgeTargetRef}
            title="Assembly, on us"
            body="This item ships with free professional assembly — no extra charge at checkout."
            onDismiss={() => setSpotlightTarget(null)}
            reasonText="Shown because this product category usually prompts an assembly-fee question at checkout."
          />
        )}
      </div>
    </MotionPreferenceProvider>
  );
}
