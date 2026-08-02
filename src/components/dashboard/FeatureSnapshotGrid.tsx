export function FeatureSnapshotGrid({ features }: { features: Record<string, number> }) {
  const groups = Object.entries(features).reduce<Record<string, Array<[string, number]>>>((result, entry) => {
    const prefix = entry[0].split("_", 1)[0];
    (result[prefix] ??= []).push(entry);
    return result;
  }, {});
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-sm font-semibold text-white">Feature snapshot</h2>
      <p className="mt-1 text-xs text-slate-500">The exact serving vector persisted with this decision.</p>
      <div className="mt-5 space-y-5">
        {Object.entries(groups).map(([prefix, entries]) => (
          <div key={prefix}>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-400">{prefix} features</p>
            <dl className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {entries.map(([name, value]) => (
                <div key={name} className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2">
                  <dt className="truncate font-mono text-[10px] text-slate-500" title={name}>{name}</dt>
                  <dd className="mt-1 font-mono text-sm font-semibold text-slate-200">{Number(value).toLocaleString("en-IN", { maximumFractionDigits: 3 })}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}
