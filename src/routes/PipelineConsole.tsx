import {
  ArrowRight,
  BrainCircuit,
  Database,
  ExternalLink,
  Layers,
  MessageSquareText,
  RefreshCw,
  Scale,
  ShieldCheck,
  Target,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { useTracker } from "../context/TrackerContext";

const AGENTS = [
  { icon: Layers, name: "Feature Agent", detail: "Rebuilds 67 signals from the event log" },
  { icon: BrainCircuit, name: "Risk Agent", detail: "Calibrated abandonment probability" },
  { icon: Target, name: "Reasoning Agent", detail: "Ranks supported root causes" },
  { icon: ShieldCheck, name: "Policy Agent", detail: "11 safety rules, before any ranking" },
  { icon: Scale, name: "Recommendation Agent", detail: "Utility ranking over approved actions" },
  { icon: MessageSquareText, name: "Explainability Agent", detail: "Grounded justification trail" },
];

interface ExplanationShape {
  inference?: { root_cause?: string };
  rendered_text?: string;
}

function humanise(value: string): string {
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b[a-z]/g, (character) => character.toUpperCase());
}

/**
 * The shopper-facing view of what the backend is doing.
 *
 * This used to be a grid of zeroed counters in a colour scheme borrowed from
 * nowhere in particular. It now shows the same agent chain the dashboard shows,
 * in the storefront's own theme, against the live session.
 */
export default function PipelineConsole() {
  const { snapshot, loading, error, refresh } = useTracker();
  const { latestDecision } = useSession();

  const counters = Object.entries(snapshot?.counters ?? {})
    .filter(([, value]) => value > 0)
    .sort(([left], [right]) => left.localeCompare(right));
  const explanation = (latestDecision?.explanation ?? {}) as ExplanationShape;
  const probability = latestDecision?.abandonment_probability;
  const displayPct =
    probability === undefined ? null : Math.min(99, Math.max(1, Math.round(probability * 100)));

  return (
    <div className="flex flex-col gap-3">
      <header className="rounded-[2px] border border-fk-border bg-white p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-[2px] bg-fk-blue text-white">
            <Database className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h1 className="text-fk-xl font-bold text-fk-ink">Decision pipeline</h1>
            <p className="text-fk-sm text-fk-muted">
              Browser events → validated ingestion → replayable state → governed decision
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Link
              to="/dashboard"
              className="flex items-center gap-1.5 rounded-[2px] border border-fk-border px-3 py-2 text-fk-sm font-medium text-fk-blue hover:bg-fk-bg"
            >
              Operations dashboard
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
            <button
              type="button"
              onClick={refresh}
              className="flex items-center gap-1.5 rounded-[2px] bg-fk-blue px-3 py-2 text-fk-sm font-medium text-white hover:bg-fk-blue-dark"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {error && (
        <section className="rounded-[2px] border border-amber-200 bg-amber-50 p-4 text-fk-md text-amber-900">
          The event API is unavailable. Storefront interactions continue and remain buffered locally.
        </section>
      )}

      <section className="rounded-[2px] border border-fk-border bg-white p-5">
        <h2 className="text-fk-lg font-medium text-fk-ink">Agents in this decision path</h2>
        <p className="mt-1 text-fk-sm text-fk-muted">
          Each stage is specialised and ordered. Policy always runs before ranking, so a confident
          model can never route around a safety rule.
        </p>
        <ol className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map(({ icon: Icon, name, detail }, index) => (
            <li
              key={name}
              className="flex items-start gap-3 rounded-[2px] border border-fk-border bg-fk-bg p-3"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[2px] bg-white text-fk-blue">
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <p className="text-fk-md font-medium text-fk-ink">
                  <span className="mr-1.5 text-fk-muted">{index + 1}.</span>
                  {name}
                </p>
                <p className="mt-0.5 text-fk-sm text-fk-muted">{detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_2fr]">
        <section className="rounded-[2px] border border-fk-border bg-white p-5">
          <h2 className="text-fk-lg font-medium text-fk-ink">Canonical session</h2>
          {snapshot ? (
            <dl className="mt-4 space-y-3 text-fk-sm">
              <div>
                <dt className="text-fk-muted">Session ID</dt>
                <dd className="mt-1 break-all font-mono text-fk-ink">{snapshot.session.session_id}</dd>
              </div>
              <div>
                <dt className="text-fk-muted">Route</dt>
                <dd className="mt-1 font-medium text-fk-ink">{snapshot.session.current_route ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-fk-muted">Current product</dt>
                <dd className="mt-1 font-medium text-fk-ink">
                  {snapshot.session.current_product_id ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-fk-muted">Last event</dt>
                <dd className="mt-1 font-medium text-fk-ink">
                  {snapshot.session.last_event_at
                    ? new Date(snapshot.session.last_event_at).toLocaleTimeString()
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-fk-muted">Cart</dt>
                <dd className="mt-1 font-medium text-fk-ink">
                  {snapshot.cart.item_count} items · ₹{snapshot.cart.value.toLocaleString("en-IN")}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-4 text-fk-sm text-fk-muted">Waiting for the first event batch.</p>
          )}
        </section>

        <section className="rounded-[2px] border border-fk-border bg-white p-5">
          <h2 className="text-fk-lg font-medium text-fk-ink">Latest decision</h2>
          {latestDecision?.decision_id ? (
            <div className="mt-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-[2px] border border-fk-border bg-fk-bg p-3">
                  <p className="text-fk-xs uppercase tracking-wide text-fk-muted">Risk</p>
                  <p className="mt-1 text-fk-xl font-bold text-fk-ink">
                    {displayPct === null ? "—" : `${displayPct}%`}
                  </p>
                  <p className="text-fk-sm text-fk-muted">{latestDecision.risk_level ?? "—"}</p>
                </div>
                <div className="rounded-[2px] border border-fk-border bg-fk-bg p-3">
                  <p className="text-fk-xs uppercase tracking-wide text-fk-muted">Likely reason</p>
                  <p className="mt-1 text-fk-md font-medium text-fk-ink">
                    {explanation.inference?.root_cause
                      ? humanise(explanation.inference.root_cause)
                      : "Not diagnosed"}
                  </p>
                </div>
                <div className="rounded-[2px] border border-fk-border bg-fk-bg p-3">
                  <p className="text-fk-xs uppercase tracking-wide text-fk-muted">Decision</p>
                  <p className="mt-1 text-fk-md font-medium text-fk-blue">
                    {latestDecision.decision === "INTERVENE"
                      ? humanise(latestDecision.recommended_intervention?.type ?? "")
                      : humanise(latestDecision.decision ?? "")}
                  </p>
                </div>
              </div>
              {explanation.rendered_text && (
                <p className="mt-3 rounded-[2px] border border-fk-border bg-fk-bg p-3 text-fk-md leading-relaxed text-fk-ink">
                  {explanation.rendered_text}
                </p>
              )}
              <Link
                to={`/dashboard/decisions/${latestDecision.decision_id}`}
                className="mt-3 inline-flex items-center gap-1.5 text-fk-md font-medium text-fk-blue"
              >
                Open the full decision trace
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          ) : (
            <p className="mt-4 rounded-[2px] border border-dashed border-fk-border p-8 text-center text-fk-sm text-fk-muted">
              No decision yet. Add something to your cart, open reviews a few times, then return here.
            </p>
          )}

          <h3 className="mt-6 text-fk-md font-medium text-fk-ink">Server-side counters</h3>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {counters.map(([name, value]) => (
              <div key={name} className="rounded-[2px] border border-fk-border bg-fk-bg px-3 py-3">
                <p className="truncate text-fk-xs uppercase tracking-wide text-fk-muted" title={name}>
                  {name.replaceAll("_", " ")}
                </p>
                <p className="mt-1 text-fk-lg font-bold text-fk-ink">
                  {value.toLocaleString("en-IN")}
                </p>
              </div>
            ))}
            {counters.length === 0 && (
              <p className="col-span-full rounded-[2px] border border-dashed border-fk-border p-8 text-center text-fk-sm text-fk-muted">
                No signals captured yet.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
