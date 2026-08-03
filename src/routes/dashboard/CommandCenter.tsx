import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  CircleDot,
  ExternalLink,
  Radio,
  RefreshCw,
  Search,
  ShoppingCart,
  WifiOff,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { DecisionPipeline } from "../../components/dashboard/DecisionPipeline";
import { useActiveSessions } from "../../hooks/useActiveSessions";
import { useDecisionTrace } from "../../hooks/useDecisionTrace";
import { useSessionDetail } from "../../hooks/useSessionDetail";
import { formatProbability, formatRupees, timeAgo, titleCase } from "../../lib/metrics";
import type { ActiveSession, DecisionSummary, SessionDetailResponse } from "../../types/dashboard";

type SessionFilter = "all" | "high" | "intervened" | "silent";

const FILTERS: Array<{ id: SessionFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "high", label: "High risk" },
  { id: "intervened", label: "Acted" },
  { id: "silent", label: "Silent" },
];

const DECISION_TONE: Record<string, string> = {
  INTERVENE: "border-teal-400/30 bg-teal-400/10 text-teal-200",
  NO_ACTION: "border-zinc-600 bg-zinc-700/30 text-zinc-300",
  ABSTAIN: "border-amber-400/30 bg-amber-400/10 text-amber-200",
};

function matchesFilter(session: ActiveSession, filter: SessionFilter): boolean {
  const decision = session.latest_decision;
  if (filter === "all") return true;
  if (!decision) return false;
  if (filter === "high") return decision.risk_band === "HIGH";
  if (filter === "intervened") return decision.decision === "INTERVENE";
  return decision.decision !== "INTERVENE";
}

function sessionLabel(sessionId: string): string {
  const scenario = /^demo-([a-h])-(\d+)(?:-(\d+))?$/i.exec(sessionId);
  if (scenario) {
    const suffix = scenario[3]
      ? `Run ${scenario[3].slice(-4)}`
      : `Session ${Number(scenario[2]) + 1}`;
    return `Scenario ${scenario[1].toUpperCase()} / ${suffix}`;
  }
  return sessionId.length > 18 ? `${sessionId.slice(0, 8)}...${sessionId.slice(-5)}` : sessionId;
}

function SessionRail({
  sessions,
  selectedId,
  loading,
  filter,
  query,
  onFilter,
  onQuery,
}: {
  sessions: ActiveSession[];
  selectedId: string | undefined;
  loading: boolean;
  filter: SessionFilter;
  query: string;
  onFilter: (filter: SessionFilter) => void;
  onQuery: (query: string) => void;
}) {
  return (
    <aside className="min-h-0 border border-zinc-800 bg-[#0d1117]">
      <header className="border-b border-zinc-800 px-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-300">Live queue</p>
            <h2 className="mt-1 text-sm font-semibold text-white">Shopping sessions</h2>
          </div>
          <span className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[10px] text-zinc-400">
            {sessions.length}
          </span>
        </div>

        <label className="relative mt-3 block">
          <span className="sr-only">Filter sessions</span>
          <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-600" />
          <input
            value={query}
            onChange={(event) => onQuery(event.target.value)}
            placeholder="Find a session"
            className="h-9 w-full border border-zinc-800 bg-black/20 pl-9 pr-3 text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-blue-400 focus:outline-none"
          />
        </label>

        <div className="mt-3 grid grid-cols-2 gap-1" role="group" aria-label="Session filter">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onFilter(item.id)}
              aria-pressed={filter === item.id}
              className={`h-8 cursor-pointer border px-2 text-[10px] font-semibold transition ${
                filter === item.id
                  ? "border-blue-400/45 bg-blue-400/10 text-blue-200"
                  : "border-transparent text-zinc-500 hover:border-zinc-700 hover:text-zinc-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>

      <div className="max-h-[300px] overflow-y-auto xl:max-h-[calc(100vh-265px)]">
        {loading && sessions.length === 0 && (
          <div className="space-y-2 p-3" aria-label="Loading sessions">
            {[0, 1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse bg-zinc-900" />)}
          </div>
        )}

        {!loading && sessions.length === 0 && (
          <div className="px-5 py-12 text-center">
            <CircleDot className="mx-auto h-6 w-6 text-zinc-600" />
            <p className="mt-3 text-xs font-medium text-zinc-300">No matching sessions</p>
            <Link to="/dashboard/proof/scenarios" className="mt-3 inline-flex text-xs text-blue-300 hover:text-blue-200">
              Run a proof scenario
            </Link>
          </div>
        )}

        <ol className="divide-y divide-zinc-800">
          {sessions.map((session) => {
            const decision = session.latest_decision;
            const selected = session.session_id === selectedId;
            return (
              <li key={session.session_id}>
                <Link
                  to={`/dashboard/sessions/${session.session_id}`}
                  aria-current={selected ? "page" : undefined}
                  className={`block min-h-28 border-l-2 px-4 py-3 transition ${
                    selected
                      ? "border-l-blue-400 bg-blue-400/8"
                      : "border-l-transparent hover:bg-white/[0.025]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`truncate font-mono text-[11px] font-semibold ${selected ? "text-blue-200" : "text-zinc-300"}`}>
                      {sessionLabel(session.session_id)}
                    </span>
                    <span className="shrink-0 text-[10px] text-zinc-600">{timeAgo(session.last_event_at)}</span>
                  </div>
                  <p className="mt-1 truncate text-[11px] text-zinc-500">
                    {session.current_route ?? "No active route"} / {session.event_count} events
                  </p>

                  {decision ? (
                    <>
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <span className={`rounded border px-1.5 py-0.5 text-[9px] font-semibold ${DECISION_TONE[decision.decision] ?? DECISION_TONE.NO_ACTION}`}>
                          {decision.decision}
                        </span>
                        <span className={`font-mono text-xs font-semibold ${decision.risk_band === "HIGH" ? "text-rose-300" : decision.risk_band === "MEDIUM" ? "text-amber-300" : "text-emerald-300"}`}>
                          {formatProbability(decision.probability)}
                        </span>
                      </div>
                      <div className="mt-2 h-1 overflow-hidden bg-zinc-800">
                        <span
                          className={`block h-full ${decision.risk_band === "HIGH" ? "bg-rose-400" : decision.risk_band === "MEDIUM" ? "bg-amber-400" : "bg-emerald-400"}`}
                          style={{ width: `${Math.max(3, decision.probability * 100)}%` }}
                        />
                      </div>
                      <p className="mt-2 truncate text-[10px] text-zinc-500">
                        {titleCase(decision.selected_intervention ?? decision.decision)}
                      </p>
                    </>
                  ) : (
                    <p className="mt-4 flex items-center gap-2 text-[10px] text-zinc-600">
                      <span className="h-1.5 w-1.5 rounded-full bg-zinc-600" /> Awaiting decision
                    </p>
                  )}
                </Link>
              </li>
            );
          })}
        </ol>
      </div>
    </aside>
  );
}

function WorkspaceSkeleton() {
  return (
    <div className="border border-zinc-800 bg-[#0d1117] p-5">
      <div className="h-20 animate-pulse bg-zinc-900" />
      <div className="mt-4 h-[560px] animate-pulse bg-zinc-900" />
    </div>
  );
}

function TraceWorkspace({
  decisionId,
  session,
}: {
  decisionId: string;
  session: SessionDetailResponse;
}) {
  const { data, loading, error } = useDecisionTrace(decisionId);
  if (loading && !data) return <WorkspaceSkeleton />;
  if (error || !data) {
    return (
      <div role="alert" className="border border-rose-400/30 bg-rose-400/10 p-5 text-sm text-rose-100">
        {error ?? "Decision trace is unavailable."}
      </div>
    );
  }
  return <DecisionPipeline trace={data} session={session} />;
}

function decisionTitle(decision: DecisionSummary): string {
  return `${new Date(decision.decision_time).toLocaleTimeString()} / ${titleCase(decision.selected_intervention ?? decision.decision)}`;
}

function SessionWorkspace({ sessionId }: { sessionId: string }) {
  const { data, loading, error, stream } = useSessionDetail(sessionId);
  const [decisionId, setDecisionId] = useState<string | null>(null);
  const decisions = useMemo(
    () => [...(data?.decisions ?? [])].sort((left, right) => right.decision_time.localeCompare(left.decision_time)),
    [data?.decisions],
  );

  useEffect(() => {
    if (decisions.length === 0) {
      setDecisionId(null);
      return;
    }
    setDecisionId((current) => decisions.some((decision) => decision.decision_id === current)
      ? current
      : decisions[0].decision_id);
  }, [decisions]);

  if (loading && !data) return <WorkspaceSkeleton />;
  if (error || !data) {
    return (
      <div role="alert" className="border border-rose-400/30 bg-rose-400/10 p-5 text-sm text-rose-100">
        {error ?? "Session context is unavailable."}
      </div>
    );
  }

  return (
    <div className="min-w-0">
      <header className="flex flex-wrap items-center justify-between gap-4 border border-b-0 border-zinc-800 bg-[#0d1117] px-5 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate font-mono text-sm font-semibold text-white">{sessionLabel(data.session.session_id)}</h2>
            <span className={`inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase ${stream.status === "connected" ? "text-emerald-300" : "text-amber-300"}`}>
              {stream.status === "connected" ? <Radio className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {stream.status === "connected" ? "Live" : "Stale"}
            </span>
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            {data.session.device_type ?? "Unknown device"} / {data.timeline.length} events / {data.cart.item_count} item / {formatRupees(data.cart.value)}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {decisions.length > 1 && (
            <label className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-500">
              Decision
              <select
                value={decisionId ?? ""}
                onChange={(event) => setDecisionId(event.target.value)}
                className="h-9 max-w-64 border border-zinc-700 bg-zinc-950 px-3 text-xs normal-case tracking-normal text-zinc-200 focus:border-blue-400 focus:outline-none"
              >
                {decisions.map((decision) => (
                  <option key={decision.decision_id} value={decision.decision_id}>{decisionTitle(decision)}</option>
                ))}
              </select>
            </label>
          )}
          <Link
            to={`/dashboard/sessions/${data.session.session_id}/replay`}
            className="inline-flex h-9 items-center gap-1.5 border border-zinc-700 px-3 text-xs text-zinc-400 transition hover:border-zinc-500 hover:text-white"
          >
            Event replay
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      {decisionId ? (
        <TraceWorkspace decisionId={decisionId} session={data} />
      ) : (
        <section className="grid min-h-[590px] place-items-center border border-zinc-800 bg-[#090d13] px-6 text-center">
          <div>
            <Activity className="mx-auto h-8 w-8 text-zinc-600" />
            <h2 className="mt-3 text-sm font-semibold text-zinc-200">Session is accumulating evidence</h2>
            <p className="mt-2 max-w-md text-xs leading-relaxed text-zinc-500">
              {data.timeline.length} validated events are available. The architecture trace will resolve when the trigger gate requests a decision.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}

export default function CommandCenter() {
  const { sessionId } = useParams();
  const { data, loading, error, refresh, stream } = useActiveSessions();
  const [filter, setFilter] = useState<SessionFilter>("all");
  const [query, setQuery] = useState("");

  const allSessions = useMemo(
    () => [...(data?.sessions ?? [])].sort((left, right) => (right.last_event_at ?? "").localeCompare(left.last_event_at ?? "")),
    [data?.sessions],
  );
  const visibleSessions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return allSessions.filter((session) => matchesFilter(session, filter) && (
      needle === ""
      || session.session_id.toLowerCase().includes(needle)
      || (session.latest_decision?.selected_intervention ?? "").toLowerCase().includes(needle)
    ));
  }, [allSessions, filter, query]);
  const selectedId = sessionId ?? allSessions.find((session) => session.latest_decision)?.session_id ?? allSessions[0]?.session_id;

  return (
    <div>
      <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-300">
            <span className={`h-2 w-2 rounded-full ${stream.status === "connected" ? "bg-emerald-300" : "bg-amber-300"}`} />
            {stream.status === "connected" ? "Decision stream connected" : "Decision stream reconnecting"}
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-white">Decision Command Center</h1>
          <p className="mt-1 text-sm text-zinc-500">Live shopper evidence, governed reasoning, and customer action on one trace.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void refresh()}
            aria-label="Refresh live sessions"
            title="Refresh live sessions"
            className="grid h-10 w-10 cursor-pointer place-items-center border border-zinc-700 text-zinc-400 transition hover:border-zinc-500 hover:text-white"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <Link
            to="/"
            className="inline-flex h-10 items-center gap-2 border border-blue-400/40 bg-blue-400/10 px-4 text-xs font-semibold text-blue-100 transition hover:bg-blue-400/20"
          >
            <ShoppingCart className="h-4 w-4" />
            Open storefront
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      {error && (
        <div role="alert" className="mb-4 flex items-center gap-2 border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
          <WifiOff className="h-4 w-4" />
          {error}. Existing session data remains visible while the stream reconnects.
        </div>
      )}

      <div className="grid min-w-0 gap-4 xl:grid-cols-[260px_minmax(0,1fr)]">
        <SessionRail
          sessions={visibleSessions}
          selectedId={selectedId}
          loading={loading}
          filter={filter}
          query={query}
          onFilter={setFilter}
          onQuery={setQuery}
        />
        <main className="min-w-0">
          {selectedId ? (
            <SessionWorkspace key={selectedId} sessionId={selectedId} />
          ) : (
            <section className="grid min-h-[690px] place-items-center border border-dashed border-zinc-700 bg-[#0d1117] px-6 text-center">
              <div>
                <CircleDot className="mx-auto h-8 w-8 text-zinc-600" />
                <h2 className="mt-3 text-sm font-semibold text-zinc-200">No active decision trace</h2>
                <p className="mt-2 max-w-md text-xs leading-relaxed text-zinc-500">
                  Browse the storefront or run a deterministic scenario to populate the live architecture.
                </p>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  <Link to="/" className="inline-flex h-10 items-center gap-2 border border-blue-400/40 bg-blue-400/10 px-4 text-xs font-semibold text-blue-100">
                    <ShoppingCart className="h-4 w-4" /> Open storefront
                  </Link>
                  <Link to="/dashboard/proof/scenarios" className="inline-flex h-10 items-center gap-2 border border-zinc-700 px-4 text-xs text-zinc-300">
                    <Activity className="h-4 w-4" /> Run scenario
                  </Link>
                </div>
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
