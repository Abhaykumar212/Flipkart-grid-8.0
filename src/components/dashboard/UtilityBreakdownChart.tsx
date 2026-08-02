export function UtilityBreakdownChart({ intervention, score, breakdown, runnerUp }: { intervention: string; score: number; breakdown: Record<string, number>; runnerUp?: { intervention: string; score: number } }) {
  const terms = Object.entries(breakdown);
  const max = Math.max(...terms.map(([, value]) => Math.abs(value)), 0.01);
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-start justify-between gap-4">
        <div><h2 className="text-sm font-semibold text-white">Winner utility decomposition</h2><p className="mt-1 text-xs text-slate-500">{intervention.replaceAll("_", " ")}</p></div>
        <span className="font-mono text-xl font-semibold text-cyan-300">{score.toFixed(3)}</span>
      </div>
      <div className="mt-5 space-y-3">
        {terms.map(([term, value]) => {
          const width = Math.abs(value) / max * 50;
          return (
            <div key={term} className="grid grid-cols-[9rem_1fr_4rem] items-center gap-3">
              <span className="truncate text-right font-mono text-[10px] text-slate-500" title={term}>{term}</span>
              <div className="relative h-5">
                <span className="absolute left-1/2 top-0 h-full w-px bg-slate-600" />
                <span className={`absolute top-1 h-3 rounded-sm ${value >= 0 ? "left-1/2 bg-emerald-400" : "right-1/2 bg-rose-400"}`} style={{ width: `${width}%` }} />
              </div>
              <span className={`font-mono text-xs ${value >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{value >= 0 ? "+" : ""}{value.toFixed(3)}</span>
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap justify-between gap-2 border-t border-slate-800 pt-3 text-[11px] text-slate-500">
        <p>Signed terms sum to {Object.values(breakdown).reduce((total, value) => total + value, 0).toFixed(3)}.</p>
        {runnerUp && <p>Runner-up: <span className="font-mono text-slate-300">{runnerUp.intervention} {runnerUp.score.toFixed(3)}</span></p>}
      </div>
    </section>
  );
}
