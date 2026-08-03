import { useMemo, useState } from "react";
import { Radio, RefreshCw, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { SessionTable } from "../../components/dashboard/SessionTable";
import { Panel, StatTile } from "../../components/dashboard/Panel";
import { formatPercent, formatRupees, titleCase } from "../../lib/metrics";
import { useActiveSessions } from "../../hooks/useActiveSessions";
import { useOverview } from "../../hooks/useOverview";
import type { ActiveSession } from "../../types/dashboard";

type Filter = "all" | "intervened" | "silent" | "high";

const FILTERS: Array<{ id: Filter; label: string }> = [
  { id: "all", label: "All sessions" },
  { id: "high", label: "High risk" },
  { id: "intervened", label: "Intervened" },
  { id: "silent", label: "Left alone" },
];

function matches(session: ActiveSession, filter: Filter): boolean {
  const decision = session.latest_decision;
  if (filter === "all") return true;
  if (!decision) return false;
  if (filter === "high") return decision.risk_band === "HIGH";
  if (filter === "intervened") return decision.decision === "INTERVENE";
  return decision.decision !== "INTERVENE";
}

/** Aggregate outcomes across everything the agent has decided so far. */
function OverviewStrip() {
  const { data } = useOverview();
  if (!data || data.decisions === 0) return null;
  const { outcomes } = data;
  return (
    <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <StatTile
        label="Decisions made"
        value={data.decisions.toLocaleString("en-IN")}
        hint={`${data.sessions.toLocaleString("en-IN")} sessions observed`}
      />
      <StatTile
        label="Intervened"
        value={formatPercent(data.intervention_rate, 0)}
        hint={`${formatPercent(data.restraint_rate, 0)} deliberately left alone`}
      />
      <StatTile
        label="Engagement"
        value={formatPercent(outcomes.ctr, 1)}
        tone={outcomes.ctr > 0.25 ? "good" : "default"}
        hint={`${formatPercent(outcomes.dismissal_rate, 1)} dismissed`}
      />
      <StatTile
        label="Discount spend"
        value={formatRupees(data.discount_spend)}
        tone={data.discount_spend === 0 ? "good" : "warn"}
        hint={data.discount_spend === 0 ? "Margin fully protected" : "Granted under policy"}
      />
      <StatTile
        label="Decision p95"
        value={data.latency_ms.total ? `${data.latency_ms.total.p95.toFixed(0)} ms` : "—"}
        tone={(data.latency_ms.total?.p95 ?? 0) <= 300 ? "good" : "warn"}
        hint="Real-time budget 300 ms"
      />
    </div>
  );
}

/** Which reasons for hesitation the agent is actually seeing. */
function CauseMix() {
  const { data } = useOverview();
  const causes = Object.entries(data?.by_cause ?? {}).slice(0, 6);
  if (causes.length === 0) return null;
  const max = Math.max(...causes.map(([, count]) => count));
  return (
    <Panel
      title="Diagnosed causes"
      subtitle="Why shoppers are hesitating, across every decision on record."
      className="mb-6"
    >
      <ul className="space-y-3">
        {causes.map(([cause, count]) => (
          <li key={cause}>
            <div className="mb-1 flex items-center justify-between gap-4 text-xs">
              <span className="truncate text-slate-300">{titleCase(cause)}</span>
              <span className="shrink-0 font-mono text-slate-500">{count}</span>
            </div>
            <span className="block h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
              <span
                className="block h-full rounded-full bg-cyan-400"
                style={{ width: `${Math.max(2, (count / max) * 100)}%` }}
              />
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export default function LiveSessions() {
  const { data, loading, error, refresh, stream } = useActiveSessions();
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  // `data?.sessions ?? []` would mint a new array on every render and defeat
  // the memoised filtering below.
  const sessions = useMemo(() => data?.sessions ?? [], [data]);
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return sessions.filter(
      (session) =>
        matches(session, filter)
        && (needle === ""
          || session.session_id.toLowerCase().includes(needle)
          || (session.latest_decision?.selected_intervention ?? "").toLowerCase().includes(needle)),
    );
  }, [sessions, filter, query]);

  const counts = useMemo(
    () =>
      Object.fromEntries(
        FILTERS.map(({ id }) => [id, sessions.filter((session) => matches(session, id)).length]),
      ) as Record<Filter, number>,
    [sessions],
  );

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-cyan-300">
            <Radio className={`h-3.5 w-3.5 ${stream.status === "connected" ? "animate-pulse" : ""}`} />
            {stream.status === "connected"
              ? "Live stream connected"
              : stream.status === "reconnecting"
                ? "Reconnecting to live stream"
                : "Connecting to live stream"}
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Active shopping sessions</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Observe shopper context and move from a live session to its complete decision trail.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard/scenarios"
            className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/20"
          >
            Run a scenario
          </Link>
          <button
            onClick={() => void refresh()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300 hover:border-slate-600 hover:text-white"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>
      </header>

      <OverviewStrip />

      {error && (
        <div role="alert" className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-1 rounded-lg border border-slate-800 bg-slate-900 p-1">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setFilter(item.id)}
              aria-pressed={filter === item.id}
              className={`rounded px-3 py-1.5 text-xs transition ${
                filter === item.id
                  ? "bg-cyan-500/15 font-semibold text-cyan-200"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {item.label}
              <span className="ml-1.5 font-mono text-[10px] text-slate-500">{counts[item.id]}</span>
            </button>
          ))}
        </div>
        <label className="relative flex min-w-56 flex-1 items-center sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
          <span className="sr-only">Filter sessions</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter by session or intervention"
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2 pl-9 pr-3 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none"
          />
        </label>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_300px]">
        <div className="min-w-0">
          {loading && !data ? (
            <div className="h-72 animate-pulse rounded-xl border border-slate-800 bg-slate-900" />
          ) : (
            <SessionTable sessions={visible} />
          )}
          <p className="mt-4 text-right font-mono text-[10px] text-slate-600">
            showing {visible.length} of {sessions.length} · {stream.eventCount} live events this connection
          </p>
        </div>
        <div className="min-w-0">
          <CauseMix />
        </div>
      </div>
    </div>
  );
}
