import { RefreshCw, Radio } from "lucide-react";
import { SessionTable } from "../../components/dashboard/SessionTable";
import { useActiveSessions } from "../../hooks/useActiveSessions";

export default function LiveSessions() {
  const { data, loading, error, refresh, stream } = useActiveSessions();
  return (
    <div>
      <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-cyan-300"><Radio className={`h-3.5 w-3.5 ${stream.status === "connected" ? "animate-pulse" : ""}`} />{stream.status === "connected" ? "Live stream connected" : stream.status === "reconnecting" ? "Reconnecting to live stream" : "Connecting to live stream"}</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Active shopping sessions</h1>
          <p className="mt-2 text-sm text-slate-400">Observe shopper context and move from a live session to its complete decision trail.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-400"><strong className="mr-1 text-white">{data?.count ?? 0}</strong> active</span>
          <button onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300 hover:border-slate-600 hover:text-white"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
        </div>
      </header>
      {error && <div role="alert" className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>}
      {loading && !data ? <div className="h-72 animate-pulse rounded-xl border border-slate-800 bg-slate-900" /> : <SessionTable sessions={data?.sessions ?? []} />}
      <p className="mt-4 text-right font-mono text-[10px] text-slate-600">{stream.eventCount} live events received this connection</p>
    </div>
  );
}
