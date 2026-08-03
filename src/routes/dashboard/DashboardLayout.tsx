import {
  Activity,
  BarChart3,
  ExternalLink,
  FlaskConical,
  Network,
  PlayCircle,
  RadioTower,
} from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/dashboard", end: true, icon: Activity, label: "Live sessions" },
  { to: "/dashboard/scenarios", end: false, icon: PlayCircle, label: "Scenarios" },
  { to: "/dashboard/metrics", end: false, icon: BarChart3, label: "Models" },
  { to: "/dashboard/experiments", end: false, icon: FlaskConical, label: "Experiments" },
  { to: "/dashboard/architecture", end: false, icon: Network, label: "Architecture" },
];

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-5 py-3 lg:px-8">
          <Link to="/dashboard" className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-400 text-slate-950">
              <RadioTower className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-sm font-bold tracking-tight">Decision Intelligence</span>
              <span className="block text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Flipkart GRiD · Live operations
              </span>
            </span>
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-xs">
            {NAV.map(({ to, end, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 rounded-lg px-3 py-2 transition ${
                    isActive ? "bg-slate-800 text-cyan-300" : "text-slate-400 hover:text-white"
                  }`
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </NavLink>
            ))}
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-slate-400 hover:text-white"
            >
              Storefront
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1600px] px-5 py-7 lg:px-8 lg:py-9">
        <Outlet />
      </main>
    </div>
  );
}
