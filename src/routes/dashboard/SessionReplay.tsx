import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { OutcomeBadge } from "../../components/dashboard/OutcomeBadge";
import { PageHeader, Panel, StatTile } from "../../components/dashboard/Panel";
import { formatProbability, titleCase } from "../../lib/metrics";
import { useSessionDetail } from "../../hooks/useSessionDetail";
import type { SessionEvent } from "../../types/dashboard";

const STEP_MS = 700;

/** Behaviour counters the decision path actually keys on. */
const COUNTED: Array<{ label: string; types: string[] }> = [
  { label: "Product views", types: ["PRODUCT_VIEWED"] },
  { label: "Review opens", types: ["REVIEW_OPENED"] },
  { label: "Similar viewed", types: ["SIMILAR_PRODUCT_VIEWED"] },
  { label: "Comparisons", types: ["PRODUCT_COMPARED"] },
  { label: "Cart adds", types: ["ITEM_ADDED_TO_CART"] },
  { label: "Cart views", types: ["CART_VIEWED"] },
  { label: "Delivery checks", types: ["DELIVERY_CHECKED"] },
  { label: "Coupon searches", types: ["COUPON_SEARCHED"] },
  { label: "Checkout starts", types: ["CHECKOUT_STARTED"] },
  { label: "Payment failures", types: ["PAYMENT_FAILED"] },
];

function eventTime(event: SessionEvent): number {
  return new Date(event.server_timestamp || event.client_timestamp).getTime();
}

export default function SessionReplay() {
  const { sessionId = "" } = useParams();
  const { data, loading, error } = useSessionDetail(sessionId);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const activeRef = useRef<HTMLLIElement | null>(null);

  const timeline = useMemo(() => data?.timeline ?? [], [data]);
  const lastIndex = Math.max(0, timeline.length - 1);

  useEffect(() => {
    if (!playing) return;
    if (cursor >= lastIndex) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => setCursor((value) => Math.min(lastIndex, value + 1)), STEP_MS);
    return () => window.clearTimeout(timer);
  }, [playing, cursor, lastIndex]);

  useEffect(() => {
    // jsdom has no layout engine, so this is absent under test.
    activeRef.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [cursor]);

  if (loading && !data) return <div className="h-96 animate-pulse rounded-xl bg-slate-900" />;
  if (error || !data) {
    return (
      <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">
        {error ?? "Session not found"}
      </div>
    );
  }

  const current = timeline[cursor];
  const elapsed = timeline.length
    ? Math.max(0, Math.round((eventTime(timeline[cursor]) - eventTime(timeline[0])) / 1000))
    : 0;

  // The project's central claim is that session state is rebuildable from the
  // event log. Deriving these counters on the client, step by step, is that
  // claim being demonstrated rather than asserted.
  const seen = timeline.slice(0, cursor + 1);
  const counters = COUNTED.map((item) => ({
    label: item.label,
    value: seen.filter((event) => item.types.includes(event.event_type)).length,
  })).filter((item) => item.value > 0);

  const cutoff = current ? eventTime(current) : 0;
  // A decision usually lands after the event that triggered it, so at the end
  // of the replay everything is revealed rather than stranded past the cursor.
  const atEnd = cursor >= lastIndex;
  const firedDecisions = atEnd
    ? data.decisions
    : data.decisions.filter((decision) => new Date(decision.decision_time).getTime() <= cutoff);
  const nextDecision = atEnd
    ? undefined
    : data.decisions.find((decision) => new Date(decision.decision_time).getTime() > cutoff);

  return (
    <div>
      <Link
        to={`/dashboard/sessions/${sessionId}`}
        className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-cyan-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Session detail
      </Link>
      <div className="mt-3">
        <PageHeader
          eyebrow="Replay"
          title="Session replay"
          description="Step through the immutable event log and watch the session state the decision path sees rebuild itself."
        />
      </div>

      <Panel className="mb-5">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => {
              if (cursor >= lastIndex) setCursor(0);
              setPlaying((value) => !value);
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/20"
          >
            {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            {playing ? "Pause" : "Play"}
          </button>
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Previous event"
              onClick={() => {
                setPlaying(false);
                setCursor((value) => Math.max(0, value - 1));
              }}
              className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-400 hover:text-white"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              aria-label="Next event"
              onClick={() => {
                setPlaying(false);
                setCursor((value) => Math.min(lastIndex, value + 1));
              }}
              className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-400 hover:text-white"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              aria-label="Restart"
              onClick={() => {
                setPlaying(false);
                setCursor(0);
              }}
              className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-400 hover:text-white"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          </div>
          <label className="flex min-w-48 flex-1 items-center gap-3">
            <span className="sr-only">Replay position</span>
            <input
              type="range"
              min={0}
              max={lastIndex}
              value={cursor}
              onChange={(event) => {
                setPlaying(false);
                setCursor(Number(event.target.value));
              }}
              className="w-full accent-cyan-400"
            />
          </label>
          <span className="font-mono text-xs text-slate-400">
            {timeline.length ? cursor + 1 : 0} / {timeline.length} · +{elapsed}s
          </span>
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[1fr_.85fr]">
        <Panel title="Event log" subtitle="Server-ordered and immutable.">
          <ol className="max-h-[28rem] space-y-1.5 overflow-y-auto pr-1">
            {timeline.map((event, index) => {
              const isPast = index <= cursor;
              const isCurrent = index === cursor;
              return (
                <li
                  key={event.event_id}
                  ref={isCurrent ? activeRef : undefined}
                  className={`flex items-center justify-between gap-3 rounded-md px-3 py-2 text-xs transition ${
                    isCurrent
                      ? "border border-cyan-500/40 bg-cyan-500/10"
                      : isPast
                        ? "bg-slate-950/60"
                        : "bg-slate-950/20 opacity-40"
                  }`}
                >
                  <span className="font-mono text-cyan-200">{event.sequence_no}</span>
                  <span className={`flex-1 ${isCurrent ? "font-semibold text-white" : "text-slate-300"}`}>
                    {event.event_type.replaceAll("_", " ")}
                  </span>
                  {event.product_id && (
                    <span className="font-mono text-[10px] text-slate-600">{event.product_id}</span>
                  )}
                  <span className="text-slate-500">
                    {new Date(event.server_timestamp).toLocaleTimeString()}
                  </span>
                </li>
              );
            })}
            {timeline.length === 0 && (
              <li className="rounded-md border border-dashed border-slate-700 p-6 text-center text-xs text-slate-500">
                This session has no events yet.
              </li>
            )}
          </ol>
        </Panel>

        <div className="min-w-0 space-y-5">
          <Panel
            title={`State after event ${timeline.length ? cursor + 1 : 0}`}
            subtitle="Rebuilt from the events replayed so far."
          >
            {counters.length === 0 ? (
              <p className="text-xs text-slate-500">No behavioural signals accumulated yet.</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {counters.map((item) => (
                  <div key={item.label} className="rounded-lg bg-slate-950/50 px-3 py-2.5">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">{item.label}</p>
                    <p className="mt-0.5 text-sm font-semibold text-white">{item.value}</p>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel
            title="Decisions"
            subtitle={
              nextDecision
                ? "Keep playing to reach the next decision."
                : "Every decision this session produced."
            }
          >
            <div className="space-y-3">
              {firedDecisions.map((decision) => (
                <Link
                  key={decision.decision_id}
                  to={`/dashboard/decisions/${decision.decision_id}`}
                  className="block rounded-lg border border-slate-800 bg-slate-950/60 p-3 transition hover:border-cyan-500/30"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-white">
                      <Sparkles className="h-3.5 w-3.5 text-cyan-300" />
                      {decision.decision} · {titleCase(decision.selected_intervention ?? "No action")}
                    </span>
                    <OutcomeBadge outcome={data.outcomes[decision.decision_id] ?? null} />
                  </div>
                  <p className="mt-1.5 text-[11px] text-slate-500">
                    {formatProbability(decision.probability)} risk ·{" "}
                    {(decision.confidence * 100).toFixed(0)}% confidence · triggered by{" "}
                    {titleCase(decision.trigger)}
                  </p>
                  <p className="mt-1 font-mono text-[10px] text-slate-600">{decision.decision_id}</p>
                </Link>
              ))}
              {firedDecisions.length === 0 && (
                <p className="rounded-lg border border-dashed border-slate-700 p-5 text-center text-xs text-slate-500">
                  No decision had been made at this point in the session.
                </p>
              )}
              {nextDecision && (
                <p className="text-center text-[11px] text-slate-600">
                  Next decision fires at{" "}
                  {new Date(nextDecision.decision_time).toLocaleTimeString()}.
                </p>
              )}
            </div>
          </Panel>

          <div className="grid grid-cols-2 gap-3">
            <StatTile label="Events" value={timeline.length} />
            <StatTile label="Decisions" value={data.decisions.length} />
          </div>
        </div>
      </div>
    </div>
  );
}
