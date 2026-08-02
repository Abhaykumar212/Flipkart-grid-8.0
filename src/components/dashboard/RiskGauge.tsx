export function RiskGauge({ probability, band }: { probability: number; band: string }) {
  const color = band === "HIGH" ? "#fb7185" : band === "MEDIUM" ? "#fbbf24" : "#34d399";
  const degrees = Math.min(360, Math.max(0, probability * 360));
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Abandonment probability</p>
      <div className="mt-5 flex items-center gap-6">
        <div className="grid h-32 w-32 shrink-0 place-items-center rounded-full" style={{ background: `conic-gradient(${color} ${degrees}deg, #1e293b ${degrees}deg)` }}>
          <div className="grid h-24 w-24 place-items-center rounded-full bg-slate-900 text-center">
            <span>
              <strong className="block text-3xl text-white">{(probability * 100).toFixed(0)}%</strong>
              <small className="text-xs text-slate-500">probability</small>
            </span>
          </div>
        </div>
        <div>
          <span className="text-xs text-slate-500">Risk band</span>
          <p className="mt-1 text-2xl font-semibold" style={{ color }}>{band}</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">A calibrated score used by policy and ranking—not a guarantee of abandonment.</p>
        </div>
      </div>
    </section>
  );
}
