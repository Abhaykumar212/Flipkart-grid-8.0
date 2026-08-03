export function ModelCard({ model }: { model: { model_name: string; model_version: string; model_type: string; status: string; metrics: Record<string, unknown>; trained_at: string } }) {
  return (
    <article className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{model.model_type}</p>
          <h2 className="mt-1 text-base font-semibold text-white">{model.model_name}</h2>
          <p className="mt-1 font-mono text-xs text-cyan-300">{model.model_version}</p>
        </div>
        <span className="rounded-md border border-slate-700 px-2 py-1 text-[10px] text-slate-300">{model.status}</span>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-2">
        {Object.entries(model.metrics).slice(0, 6).map(([name, value]) => (
          <div key={name} className="rounded-md bg-slate-950/60 p-2">
            <dt className="text-[10px] uppercase text-slate-500">{name.replaceAll("_", " ")}</dt>
            <dd className="mt-1 font-mono text-xs text-slate-200">{String(value)}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-slate-500">Trained {new Date(model.trained_at).toLocaleString()}</p>
    </article>
  );
}
