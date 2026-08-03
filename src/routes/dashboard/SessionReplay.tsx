import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { OutcomeBadge } from "../../components/dashboard/OutcomeBadge";
import { useSessionDetail } from "../../hooks/useSessionDetail";

export default function SessionReplay() {
  const { sessionId = "" } = useParams();
  const { data, loading, error } = useSessionDetail(sessionId);
  if (loading && !data) return <div className="h-96 animate-pulse rounded-xl bg-slate-900" />;
  if (error || !data) return <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">{error ?? "Session not found"}</div>;
  return (
    <div>
      <Link to={`/dashboard/sessions/${sessionId}`} className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-cyan-300"><ArrowLeft className="h-3.5 w-3.5" />Session detail</Link>
      <header className="mb-6 mt-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">View 15</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Session replay</h1>
      </header>
      <div className="grid gap-5 xl:grid-cols-[1fr_.8fr]">
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold text-white">Timeline</h2>
          <ol className="mt-4 space-y-2">
            {data.timeline.map((event) => <li key={event.event_id} className="flex items-center justify-between rounded-md bg-slate-950/60 px-3 py-2 text-xs"><span className="font-mono text-cyan-200">{event.sequence_no}</span><span className="text-slate-200">{event.event_type.replaceAll("_", " ")}</span><span className="text-slate-500">{new Date(event.server_timestamp).toLocaleTimeString()}</span></li>)}
          </ol>
        </section>
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold text-white">Decisions and outcomes</h2>
          <div className="mt-4 space-y-3">
            {data.decisions.map((decision) => <Link key={decision.decision_id} to={`/dashboard/decisions/${decision.decision_id}`} className="block rounded-md bg-slate-950/60 p-3 text-sm hover:bg-slate-800"><div className="flex items-center justify-between gap-3"><span className="font-mono text-cyan-300">{decision.decision_id}</span><OutcomeBadge outcome={data.outcomes[decision.decision_id] ?? null} /></div><p className="mt-2 text-slate-300">{decision.decision} · {decision.selected_intervention ?? "NO_ACTION"}</p></Link>)}
          </div>
        </section>
      </div>
    </div>
  );
}
