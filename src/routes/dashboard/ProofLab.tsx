import {
  Activity,
  BarChart3,
  FlaskConical,
  Gauge,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const TABS = [
  { to: "/dashboard/proof/scenarios", label: "Scenarios", icon: Activity },
  { to: "/dashboard/proof/experiment", label: "Experiment", icon: FlaskConical },
  { to: "/dashboard/proof/models", label: "Models", icon: BarChart3 },
  { to: "/dashboard/proof/runtime", label: "Runtime", icon: Gauge },
];

export default function ProofLab() {
  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-300">Evaluation evidence</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Proof Lab</h1>
          <p className="mt-1 text-sm text-zinc-500">Deterministic cases, measured behavior, and serving health.</p>
        </div>
        <nav aria-label="Proof Lab views" className="flex flex-wrap items-center gap-1 border border-zinc-800 bg-[#0d1117] p-1">
          {TABS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `inline-flex h-9 items-center gap-2 px-3 text-xs font-medium transition ${
                isActive ? "bg-amber-400/10 text-amber-200" : "text-zinc-500 hover:bg-white/[0.03] hover:text-white"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <Outlet />
    </div>
  );
}

