import { useEffect, useState } from "react";
import { FlaskConical, RefreshCw } from "lucide-react";
import { getVariant } from "../lib/abTesting";

interface VariantStats {
  sessions: number;
  runs_intervened: number;
  runs_held: number;
  runs_total: number;
  silence_rate: number;
  accepted: number;
  dismissed: number;
  converted: number;
  accept_rate: number;
}

interface Summary {
  label_a: string;
  label_b: string;
  variants: { a: VariantStats; b: VariantStats };
}

/**
 * A/B testing framework — live comparison of the two delivery-policy arms
 * assigned by `backend/ab_testing.py` and applied in
 * `interventionPolicy.ts`'s `selectSurface` (see the `abVariant` branch
 * there). Reads `GET /api/ab-summary`, which aggregates every session's
 * `decisions`/`intervention_events` rows by arm — real numbers accumulated
 * across whatever demo sessions have run, not simulated.
 */
export default function ABTestingDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const myVariant = getVariant();

  const load = () => {
    setLoading(true);
    fetch("http://localhost:8000/api/ab-summary")
      .then((r) => r.json())
      .then(setSummary)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="flex items-center justify-between bg-white p-4 sm:p-6">
        <div>
          <h1 className="flex items-center gap-2 text-fk-lg font-semibold text-fk-ink">
            <FlaskConical className="h-5 w-5 text-fk-blue" /> A/B Test: Delivery Policy
          </h1>
          <p className="mt-1 text-fk-sm text-fk-muted">
            This browser's session is currently in arm{" "}
            <strong className="uppercase">{myVariant ?? "…"}</strong>.
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 rounded border border-fk-border px-3 py-1.5 text-fk-sm text-fk-ink hover:bg-fk-bg"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      {loading && <p className="bg-white p-6 text-center text-fk-sm text-fk-muted">Loading…</p>}

      {!loading && summary && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(["a", "b"] as const).map((key) => {
            const v = summary.variants[key];
            const label = key === "a" ? summary.label_a : summary.label_b;
            return (
              <div key={key} className="bg-white p-4 sm:p-6">
                <div className="mb-3 flex items-center gap-2">
                  <span className="rounded-full bg-blue-50 px-2.5 py-1 text-fk-xs font-bold uppercase text-fk-blue">
                    Arm {key}
                  </span>
                  <p className="text-fk-sm font-medium text-fk-ink">{label}</p>
                </div>
                <dl className="grid grid-cols-2 gap-3 text-fk-sm">
                  <Stat label="Sessions" value={v.sessions} />
                  <Stat label="Runs (total)" value={v.runs_total} />
                  <Stat label="Interventions shown" value={v.runs_intervened} />
                  <Stat label="Held (silent)" value={v.runs_held} />
                  <Stat label="Silence rate" value={`${(v.silence_rate * 100).toFixed(1)}%`} />
                  <Stat label="Accept rate" value={`${(v.accept_rate * 100).toFixed(1)}%`} />
                  <Stat label="Accepted" value={v.accepted} />
                  <Stat label="Dismissed" value={v.dismissed} />
                  <Stat label="Converted" value={v.converted} highlight />
                </dl>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div>
      <dt className="text-fk-xs text-fk-muted">{label}</dt>
      <dd className={`text-fk-lg font-semibold ${highlight ? "text-green-700" : "text-fk-ink"}`}>{value}</dd>
    </div>
  );
}
