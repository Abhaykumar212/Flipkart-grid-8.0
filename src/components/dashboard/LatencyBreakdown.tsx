export function LatencyBreakdown({ latency }: { latency: Record<string, number> }) {
  const total = latency.total ?? Object.values(latency).reduce((sum, value) => sum + value, 0);
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-sm font-semibold text-white">Latency breakdown</h2>
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {Object.entries(latency).map(([stage, value]) => (
          <div key={stage} className="rounded-lg bg-slate-950/50 p-3"><p className="text-[10px] uppercase text-slate-500">{stage.replaceAll("_", " ")}</p><p className="mt-1 font-mono text-sm text-slate-200">{value.toFixed(2)} ms</p></div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">End-to-end decision: <span className="font-mono text-cyan-300">{total.toFixed(2)} ms</span></p>
    </section>
  );
}
