import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Send, Sparkles, X } from "lucide-react";
import { useTracker } from "../../context/TrackerContext";
import { sendInterventionFeedback } from "../../lib/tracker";
import { pageContext, findComparisonCandidates } from "../../lib/pageContext";
import { productById } from "../../data/products";
import {
  buildProductContext,
  sendCompanionChatMessage,
  type ChatMessagePayload,
} from "../../lib/companionChat";
import type { RecommendedIntervention } from "../../lib/pipelineTrace";

/**
 * The AI Shopping Companion — persistent across the entire journey, not just
 * at-risk carts. See the companion redesign spec for the full rationale; this
 * implements the graduated presence model (dormant / ambient / attentive /
 * active) and folds proactive suggestions into the same conversation surface
 * as reactive chat, rather than treating them as separate UI modes.
 *
 * Deliberately separate from `AgentInspector` (the internal dev tool): this
 * widget only ever shows plain language, never raw lever ids or SHAP values.
 */

type PresenceState = "dormant" | "ambient" | "attentive";

interface BaseMessage {
  id: string;
  role: "companion" | "shopper";
  text: string;
}

interface TextMessage extends BaseMessage {
  kind: "text";
}

interface InterventionMessage extends BaseMessage {
  kind: "intervention";
  intervention: RecommendedIntervention;
  alternatives: RecommendedIntervention[];
  resolvedAction: "accepted" | "dismissed" | null;
}

/**
 * A quiet, dismissible proactive offer — "want me to summarize the reviews?",
 * "want the best offer explained?" — generalized so every behavioral trigger
 * shares one accept/decline UI instead of a bespoke message kind each.
 * Accepting sends `followUpQuestion` into the conversation as if the shopper
 * asked it themselves.
 */
interface PromptOfferMessage extends BaseMessage {
  kind: "prompt-offer";
  followUpQuestion: string;
  resolved: boolean;
  /** Set only for the comparison trigger — which products to send full context for. */
  comparisonProductIds?: string[];
}

type CompanionMessage = TextMessage | InterventionMessage | PromptOfferMessage;

function newId(): string {
  return `msg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

export function CompanionWidget() {
  const { rootCause, snapshot } = useTracker();
  const pageCtx = useSyncExternalStore(pageContext.subscribe, pageContext.getSnapshot);

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<CompanionMessage[]>([]);
  const [unseenCount, setUnseenCount] = useState(0);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [showAlternativesFor, setShowAlternativesFor] = useState<string | null>(null);

  const injectedLeverIdRef = useRef<string | null>(null);
  const injectedDwellProductIdRef = useRef<string | null>(null);
  const injectedDeliveryTriggerRef = useRef<string | null>(null);
  const injectedOfferTriggerRef = useRef<string | null>(null);
  const injectedComparisonKeyRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Backend-gated interventions are already a high-confidence, "earned" moment
  // (80%+ risk, LLM-diagnosed) — worth opening for. A review-dwell offer is a
  // softer heuristic signal, so it only raises attentiveness, never opens
  // itself; see the redesign spec's distinction between "attentive" and
  // "active" for why these two triggers behave differently.
  useEffect(() => {
    const plan = rootCause?.status === "success" ? rootCause.intervention_plan : null;
    const top = plan?.top_interventions[0];
    if (!top || injectedLeverIdRef.current === top.lever_id) return;
    injectedLeverIdRef.current = top.lever_id;

    setMessages((prev) => [
      ...prev,
      {
        id: newId(),
        role: "companion",
        kind: "intervention",
        text: `${top.headline} — ${top.rationale}`,
        intervention: top,
        alternatives: plan?.top_interventions.slice(1) ?? [],
        resolvedAction: null,
      },
    ]);
    setUnseenCount((n) => n + 1);
    setIsOpen(true);
  }, [rootCause]);

  function pushPromptOffer(text: string, followUpQuestion: string, comparisonProductIds?: string[]) {
    setMessages((prev) => [
      ...prev,
      {
        id: newId(),
        role: "companion",
        kind: "prompt-offer",
        text,
        followUpQuestion,
        resolved: false,
        comparisonProductIds,
      },
    ]);
    setUnseenCount((n) => n + 1);
  }

  useEffect(() => {
    const dwellId = pageCtx.reviewDwellProductId;
    if (!dwellId || injectedDwellProductIdRef.current === dwellId) return;
    injectedDwellProductIdRef.current = dwellId;
    pushPromptOffer(
      "Want me to summarize what reviewers are saying about this one?",
      "Summarize what reviewers are saying about this product.",
    );
  }, [pageCtx.reviewDwellProductId]);

  // Repeatedly checking delivery reads as delivery-timing anxiety, not
  // curiosity — one check is normal browsing, three is a real signal.
  useEffect(() => {
    const productId = pageCtx.currentProductId;
    const checks = snapshot.features.delivery_pincode_checks;
    if (!productId || checks < 3 || injectedDeliveryTriggerRef.current === productId) return;
    injectedDeliveryTriggerRef.current = productId;
    pushPromptOffer(
      "Still checking delivery for this pincode? I can walk you through exactly when this would arrive.",
      "When exactly will this be delivered, and is delivery reliable for this product?",
    );
  }, [pageCtx.currentProductId, snapshot.features.delivery_pincode_checks]);

  // Failed coupon attempts are a much stronger signal than casually opening
  // the offers panel — the shopper actively tried to save money and hit a
  // wall, which is exactly the moment to walk them through what does work.
  useEffect(() => {
    const productId = pageCtx.currentProductId;
    const failedCoupons = snapshot.features.failed_coupon_attempts;
    if (!productId || failedCoupons < 1 || injectedOfferTriggerRef.current === productId) return;
    injectedOfferTriggerRef.current = productId;
    pushPromptOffer(
      "Looks like a coupon didn't apply — want me to walk you through the best offer that actually works here?",
      "Walk me through the best available offer, bank discount, and EMI option for this product.",
    );
  }, [pageCtx.currentProductId, snapshot.features.failed_coupon_attempts]);

  // Active memory: the shopper never has to say "I'm comparing phones" —
  // visiting three similar-priced products in the same category this session
  // already says it. Keyed on the sorted product-id set so a *different*
  // cluster (comparing a different trio later) can still trigger again.
  useEffect(() => {
    const candidates = findComparisonCandidates(pageCtx.visitHistory);
    if (!candidates) return;
    const key = candidates.map((c) => c.productId).sort().join(",");
    if (injectedComparisonKeyRef.current === key) return;
    injectedComparisonKeyRef.current = key;

    const category = candidates[0].category;
    pushPromptOffer(
      `I noticed you've been comparing a few ${category} — want me to put them side by side?`,
      `Compare the ${candidates.length} products I've been looking at (${candidates
        .map((c) => c.title)
        .join(", ")}) across price, key specs, and rating, and tell me the trade-offs.`,
      candidates.map((c) => c.productId),
    );
  }, [pageCtx.visitHistory]);

  useEffect(() => {
    if (isOpen) setUnseenCount(0);
  }, [isOpen]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isOpen]);

  const presence: PresenceState =
    unseenCount > 0
      ? "attentive"
      : pageCtx.currentProductId || snapshot.signals.cartActive
        ? "ambient"
        : "dormant";

  function historyPayload(extra?: ChatMessagePayload): ChatMessagePayload[] {
    const fromThread: ChatMessagePayload[] = messages.map((m) => ({
      role: m.role === "companion" ? "assistant" : "user",
      content: m.text,
    }));
    return extra ? [...fromThread, extra] : fromThread;
  }

  async function sendText(text: string, comparisonProductIds?: string[]) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    const shopperMessage: TextMessage = { id: newId(), role: "shopper", kind: "text", text: trimmed };
    const history = historyPayload({ role: "user", content: trimmed });
    setMessages((prev) => [...prev, shopperMessage]);
    setDraft("");
    setSending(true);

    const product = pageCtx.currentProductId ? productById.get(pageCtx.currentProductId) : undefined;
    const productContext = product ? buildProductContext(product) : null;
    const comparisonProducts = (comparisonProductIds ?? [])
      .map((id) => productById.get(id))
      .filter((p): p is NonNullable<typeof p> => Boolean(p))
      .map(buildProductContext);

    try {
      const result = await sendCompanionChatMessage(
        productContext,
        history,
        comparisonProducts,
        pageCtx.searchHistory,
      );
      const replyText =
        result.status === "success" && result.reply
          ? result.reply
          : result.status === "rate_limited"
            ? "I'm getting a lot of questions right now — give me a few seconds and try again."
            : result.status === "not_configured"
              ? "Chat isn't set up yet on this environment."
              : "Something went wrong on my end — try again in a moment.";
      setMessages((prev) => [...prev, { id: newId(), role: "companion", kind: "text", text: replyText }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "companion", kind: "text", text: "Couldn't reach the server — try again in a moment." },
      ]);
    } finally {
      setSending(false);
    }
  }

  function respondToIntervention(message: InterventionMessage, action: "accepted" | "dismissed") {
    void sendInterventionFeedback(message.intervention.lever_id, action);
    setMessages((prev) =>
      prev.map((m) => (m.id === message.id && m.kind === "intervention" ? { ...m, resolvedAction: action } : m)),
    );
  }

  function offerAlternative(alt: RecommendedIntervention) {
    setMessages((prev) => [
      ...prev,
      {
        id: newId(),
        role: "companion",
        kind: "intervention",
        text: `${alt.headline} — ${alt.rationale}`,
        intervention: alt,
        alternatives: [],
        resolvedAction: null,
      },
    ]);
    setShowAlternativesFor(null);
  }

  function resolvePromptOffer(message: PromptOfferMessage) {
    setMessages((prev) =>
      prev.map((m) => (m.id === message.id && m.kind === "prompt-offer" ? { ...m, resolved: true } : m)),
    );
  }

  function acceptPromptOffer(message: PromptOfferMessage) {
    resolvePromptOffer(message);
    void sendText(message.followUpQuestion, message.comparisonProductIds);
  }

  return (
    // Docked to the right edge, vertically centered — a persistent companion
    // rail rather than a corner action button, and deliberately clear of
    // AgentInspector's bottom-right debug pill so the two never collide.
    <div className="fixed right-0 top-1/2 z-[9999] flex -translate-y-1/2 items-center">
      {isOpen && (
        <section className="mr-2 flex max-h-[70vh] w-[min(360px,calc(100vw-24px))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.28)]">
          <header className="flex shrink-0 items-center justify-between gap-3 bg-gradient-to-br from-emerald-600 to-teal-700 px-4 py-3 text-white">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/15">
                <Sparkles className="h-4 w-4" />
              </span>
              <div>
                <h2 className="text-sm font-bold leading-4">Shopping Assistant</h2>
                <p className="text-[10px] text-emerald-100">
                  {pageCtx.currentProductId ? "Ask me anything about this product" : "Ask me anything"}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="rounded-lg p-1.5 text-emerald-100 transition hover:bg-white/10 hover:text-white"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3">
            {messages.length === 0 && (
              <p className="px-2 py-6 text-center text-xs text-slate-400">
                {pageCtx.currentProductId
                  ? "Ask about specs, reviews, EMI options — anything about this product."
                  : "Open a product and ask me anything, or just say hi."}
              </p>
            )}
            <div className="flex flex-col gap-2.5">
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  showAlternatives={showAlternativesFor === message.id}
                  onToggleAlternatives={() =>
                    setShowAlternativesFor((id) => (id === message.id ? null : message.id))
                  }
                  onSelectAlternative={offerAlternative}
                  onAccept={(m) => respondToIntervention(m, "accepted")}
                  onDismiss={(m) => respondToIntervention(m, "dismissed")}
                  onAcceptPromptOffer={acceptPromptOffer}
                  onDeclinePromptOffer={resolvePromptOffer}
                />
              ))}
              {sending && (
                <div className="flex items-center gap-1.5 self-start rounded-lg bg-slate-100 px-3 py-2">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
                </div>
              )}
            </div>
          </div>

          <form
            className="flex shrink-0 items-center gap-2 border-t border-slate-100 p-2.5"
            onSubmit={(event) => {
              event.preventDefault();
              void sendText(draft);
            }}
          >
            <input
              type="text"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={pageCtx.currentProductId ? "Ask about this product…" : "Ask me anything…"}
              className="h-9 flex-1 rounded-full border border-slate-200 px-3.5 text-xs focus:border-emerald-400 focus:outline-none"
            />
            <button
              type="submit"
              disabled={sending || !draft.trim()}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white transition hover:bg-emerald-700 disabled:opacity-40"
              aria-label="Send"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-label={isOpen ? "Close shopping assistant" : "Open shopping assistant"}
        aria-pressed={isOpen}
        className={`flex h-24 w-12 flex-col items-center justify-center gap-1.5 rounded-l-2xl border border-r-0 border-white/20 bg-gradient-to-b from-emerald-600 to-teal-600 text-white shadow-[-6px_10px_30px_rgba(5,150,105,0.3)] transition hover:w-14 ${
          presence === "dormant" ? "opacity-55 saturate-50" : "opacity-100"
        }`}
      >
        <span className="relative flex h-7 w-7 items-center justify-center rounded-full bg-white/15">
          <Sparkles className="h-4 w-4" />
          {presence === "attentive" && (
            <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-300 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full border-2 border-emerald-600 bg-amber-300" />
            </span>
          )}
        </span>
        <span className="text-[9px] font-bold leading-tight">Ask</span>
      </button>
    </div>
  );
}

function MessageBubble({
  message,
  showAlternatives,
  onToggleAlternatives,
  onSelectAlternative,
  onAccept,
  onDismiss,
  onAcceptPromptOffer,
  onDeclinePromptOffer,
}: {
  message: CompanionMessage;
  showAlternatives: boolean;
  onToggleAlternatives: () => void;
  onSelectAlternative: (alt: RecommendedIntervention) => void;
  onAccept: (m: InterventionMessage) => void;
  onDismiss: (m: InterventionMessage) => void;
  onAcceptPromptOffer: (m: PromptOfferMessage) => void;
  onDeclinePromptOffer: (m: PromptOfferMessage) => void;
}) {
  const isShopper = message.role === "shopper";

  if (message.kind === "text") {
    return (
      <div
        className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
          isShopper ? "self-end bg-emerald-600 text-white" : "self-start bg-slate-100 text-slate-800"
        }`}
      >
        {message.text}
      </div>
    );
  }

  if (message.kind === "prompt-offer") {
    return (
      <div className="max-w-[90%] self-start rounded-xl bg-slate-100 px-3 py-2.5 text-xs text-slate-800">
        <p className="leading-relaxed">{message.text}</p>
        {!message.resolved ? (
          <div className="mt-2 flex gap-1.5">
            <button
              onClick={() => onAcceptPromptOffer(message)}
              className="rounded-full bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-700"
            >
              Yes, please
            </button>
            <button
              onClick={() => onDeclinePromptOffer(message)}
              className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:bg-white"
            >
              No thanks
            </button>
          </div>
        ) : (
          <p className="mt-1.5 text-[10px] italic text-slate-400">Noted.</p>
        )}
      </div>
    );
  }

  // kind === "intervention"
  const { intervention, alternatives, resolvedAction } = message;
  return (
    <div className="max-w-[90%] self-start rounded-xl bg-slate-100 px-3 py-2.5 text-xs text-slate-800">
      <p className="font-semibold text-slate-900">{intervention.headline}</p>
      <p className="mt-0.5 leading-relaxed text-slate-600">{intervention.rationale}</p>

      {intervention.explanation.length > 0 && (
        <details className="mt-1.5">
          <summary className="cursor-pointer select-none text-[11px] font-medium text-emerald-700 hover:text-emerald-800">
            Why am I seeing this?
          </summary>
          <ul className="mt-1 flex flex-col gap-1 border-l-2 border-emerald-100 pl-2.5 text-[11px] text-slate-500">
            {intervention.explanation.map((factor, i) => (
              <li key={`${factor.factor}-${i}`}>{factor.observation}</li>
            ))}
          </ul>
        </details>
      )}

      {resolvedAction === null ? (
        <div className="mt-2 flex gap-1.5">
          <button
            onClick={() => onAccept(message)}
            className="rounded-full bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-700"
          >
            Yes, show me
          </button>
          <button
            onClick={() => onDismiss(message)}
            className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:bg-white"
          >
            Not now
          </button>
        </div>
      ) : (
        <p className="mt-1.5 text-[10px] italic text-slate-400">
          {resolvedAction === "accepted" ? "Marked as helpful." : "Noted."}
        </p>
      )}

      {alternatives.length > 0 && (
        <div className="mt-2 border-t border-slate-200 pt-1.5">
          <button
            onClick={onToggleAlternatives}
            className="text-[10px] font-medium text-slate-500 hover:text-slate-700"
          >
            {showAlternatives ? "Hide other options" : `${alternatives.length} other option${alternatives.length > 1 ? "s" : ""}`}
          </button>
          {showAlternatives && (
            <ul className="mt-1.5 flex flex-col gap-1">
              {alternatives.map((alt) => (
                <li key={alt.lever_id}>
                  <button
                    onClick={() => onSelectAlternative(alt)}
                    className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-left text-[11px] text-slate-700 hover:border-emerald-200"
                  >
                    {alt.headline}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
