import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { MessageCircleQuestion, Send, Sparkles, X } from "lucide-react";
import { productById } from "../../data/products";
import { getReviews } from "../../lib/productDetails";
import {
  answerShoppingQuestion,
  reviewTopics,
} from "../../lib/shoppingCompanion";
import {
  findComparisonCandidates,
  shoppingContext,
} from "../../lib/shoppingContext";

interface Message {
  id: number;
  role: "assistant" | "shopper";
  text: string;
  offerPrompt?: string;
  resolved?: boolean;
}

function assistantMessage(id: number, text: string, offerPrompt?: string): Message {
  return { id, role: "assistant", text, ...(offerPrompt ? { offerPrompt } : {}) };
}

export function CompanionWidget() {
  const context = useSyncExternalStore(
    shoppingContext.subscribe,
    shoppingContext.getSnapshot,
    shoppingContext.getSnapshot,
  );
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [unseen, setUnseen] = useState(0);
  const nextMessageId = useRef(1);
  const handledReviewDwell = useRef<string | null>(null);
  const handledComparison = useRef<string | null>(null);
  const handledRequest = useRef<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const product = context.currentProductId
    ? productById.get(context.currentProductId)
    : undefined;
  const comparisonVisits = useMemo(
    () => findComparisonCandidates(context.visitHistory),
    [context.visitHistory],
  );
  const comparisonProducts = useMemo(() => (comparisonVisits ?? [])
    .map((visit) => productById.get(visit.productId))
    .filter((item): item is NonNullable<typeof item> => Boolean(item)), [comparisonVisits]);
  const quickPrompts = useMemo(() => {
    if (!product) return ["What can you help with?", "What have I searched for?"];
    const topics = reviewTopics(getReviews(product));
    return [
      "Explain the price and offers",
      topics[0] ? `What do reviews say about ${topics[0]}?` : "Summarize the reviews",
      "When will it arrive?",
    ];
  }, [product]);

  const appendAssistant = useCallback((text: string, offerPrompt?: string) => {
    setMessages((current) => [
      ...current,
      assistantMessage(nextMessageId.current++, text, offerPrompt),
    ]);
    if (!open) setUnseen((count) => count + 1);
  }, [open]);

  const send = useCallback((text: string) => {
    const question = text.trim();
    if (!question) return;
    setMessages((current) => [
      ...current,
      { id: nextMessageId.current++, role: "shopper", text: question },
      assistantMessage(nextMessageId.current++, answerShoppingQuestion(question, {
        product,
        comparisonProducts,
        searchHistory: context.searchHistory,
      })),
    ]);
    setDraft("");
    setOpen(true);
  }, [comparisonProducts, context.searchHistory, product]);

  useEffect(() => {
    const productId = context.reviewDwellProductId;
    if (!productId || handledReviewDwell.current === productId) return;
    handledReviewDwell.current = productId;
    appendAssistant(
      "You’ve been reading the reviews. Want a balanced summary of the strongest praise and concerns?",
      "Summarize the reviews",
    );
  }, [appendAssistant, context.reviewDwellProductId]);

  useEffect(() => {
    if (!comparisonVisits) return;
    const key = comparisonVisits.map((item) => item.productId).sort().join(",");
    if (handledComparison.current === key) return;
    handledComparison.current = key;
    appendAssistant(
      `I noticed you viewed ${comparisonVisits.length} similar products. Want them compared side by side?`,
      "Compare the products I viewed",
    );
  }, [appendAssistant, comparisonVisits]);

  useEffect(() => {
    const request = context.companionRequest;
    if (!request || handledRequest.current === request.id) return;
    handledRequest.current = request.id;
    setOpen(true);
    if (request.prompt) send(request.prompt);
  }, [context.companionRequest, send]);

  useEffect(() => {
    if (open) setUnseen(0);
  }, [open]);

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages, open]);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  const presence = unseen > 0 ? "attentive" : product ? "ambient" : "dormant";

  return (
    <div className="fixed bottom-4 right-3 z-40 flex flex-col items-end gap-2 sm:bottom-5 sm:right-5">
      {open && (
        <section
          aria-label="Shopping companion"
          className="flex max-h-[min(620px,75vh)] w-[min(380px,calc(100vw-24px))] flex-col overflow-hidden rounded-2xl border border-fk-border bg-white shadow-fk-hover"
        >
          <header className="flex items-center justify-between gap-3 bg-gradient-to-r from-fk-blue to-fk-blue-dark px-4 py-3 text-white">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15">
                <Sparkles className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <h2 className="text-fk-md font-medium">Shopping Companion</h2>
                <p className="text-fk-xs text-blue-100">Grounded in the product listing</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="flex h-11 w-11 items-center justify-center rounded-full hover:bg-white/10"
              aria-label="Close shopping companion"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </header>

          <div ref={scrollRef} role="log" aria-live="polite" className="min-h-48 flex-1 overflow-y-auto p-3">
            {messages.length === 0 && (
              <div className="px-2 py-5 text-center">
                <p className="text-fk-base text-fk-ink">
                  {product ? `Ask me about ${product.title}.` : "Open a product for grounded answers."}
                </p>
                <p className="mt-1 text-fk-sm text-fk-muted">No API key or network connection required.</p>
              </div>
            )}
            <div className="flex flex-col gap-2.5">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`max-w-[88%] rounded-xl px-3 py-2 text-fk-sm leading-5 whitespace-pre-line ${
                    message.role === "shopper"
                      ? "self-end bg-fk-blue text-white"
                      : "self-start bg-fk-bg text-fk-ink"
                  }`}
                >
                  <p>{message.text}</p>
                  {message.offerPrompt && !message.resolved && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setMessages((current) => current.map((item) => (
                            item.id === message.id ? { ...item, resolved: true } : item
                          )));
                          send(message.offerPrompt ?? "");
                        }}
                        className="min-h-9 rounded-full bg-fk-blue px-3 font-medium text-white"
                      >
                        Yes, please
                      </button>
                      <button
                        type="button"
                        onClick={() => setMessages((current) => current.map((item) => (
                          item.id === message.id ? { ...item, resolved: true } : item
                        )))}
                        className="min-h-9 rounded-full border border-fk-border bg-white px-3 text-fk-muted"
                      >
                        Not now
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-2 overflow-x-auto border-t border-fk-border px-3 py-2 no-scrollbar">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => send(prompt)}
                className="min-h-9 shrink-0 rounded-full border border-blue-200 bg-blue-50 px-3 text-fk-xs font-medium text-fk-blue"
              >
                {prompt}
              </button>
            ))}
          </div>

          <form
            className="flex items-center gap-2 border-t border-fk-border p-3"
            onSubmit={(event) => { event.preventDefault(); send(draft); }}
          >
            <label htmlFor="companion-question" className="sr-only">Ask the shopping companion</label>
            <input
              id="companion-question"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={product ? "Ask about this product…" : "Ask what I can help with…"}
              className="h-11 min-w-0 flex-1 rounded-full border border-fk-border px-4 text-base focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue"
            />
            <button
              type="submit"
              disabled={!draft.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-fk-blue text-white disabled:opacity-40"
              aria-label="Send question"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label={open ? "Close shopping companion" : "Open shopping companion"}
        aria-pressed={open}
        className={`relative flex min-h-12 items-center gap-2 rounded-full bg-fk-blue px-4 font-medium text-white shadow-fk-hover transition hover:bg-fk-blue-dark ${
          presence === "dormant" ? "opacity-75" : "opacity-100"
        }`}
      >
        <MessageCircleQuestion className="h-5 w-5" aria-hidden="true" />
        <span>Ask</span>
        {unseen > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-fk-flame px-1 text-[10px] font-bold" aria-label={`${unseen} new suggestions`}>
            {unseen}
          </span>
        )}
      </button>
    </div>
  );
}
