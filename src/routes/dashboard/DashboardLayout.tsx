import {
  ExternalLink,
  FlaskConical,
  LayoutDashboard,
  Network,
  Radar,
} from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/dashboard", end: true, icon: LayoutDashboard, label: "Command Center" },
  { to: "/dashboard/proof/scenarios", end: false, icon: FlaskConical, label: "Proof Lab" },
  { to: "/dashboard/architecture", end: false, icon: Network, label: "System Blueprint" },
];

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-[#070a0f] text-zinc-100">
      <a
        href="#dashboard-main"
        className="fixed left-3 top-3 z-50 -translate-y-20 bg-white px-3 py-2 text-sm text-black focus:translate-y-0"
      >
        Skip to dashboard
      </a>
      <header className="sticky top-0 z-20 border-b border-zinc-800 bg-[#070a0f]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1900px] flex-wrap items-center justify-between gap-3 px-5 py-3 lg:px-7">
          <Link to="/dashboard" className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-blue-500 text-white">
              <Radar className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-sm font-bold">Decision Intelligence</span>
              <span className="block text-[10px] uppercase tracking-[0.16em] text-zinc-600">
                Flipkart GRiD / Governed intervention
              </span>
            </span>
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-xs" aria-label="Dashboard">
            {NAV.map(({ to, end, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `inline-flex h-9 items-center gap-1.5 border-b-2 px-3 text-xs font-medium transition ${
                    isActive ? "border-blue-400 text-blue-200" : "border-transparent text-zinc-500 hover:text-white"
                  }`
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </NavLink>
            ))}
            <Link
              to="/"
              className="inline-flex h-9 items-center gap-1.5 px-3 text-zinc-500 hover:text-white"
            >
              Storefront
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </nav>
        </div>
      </header>
      <main id="dashboard-main" className="mx-auto max-w-[1900px] px-5 py-6 lg:px-7 lg:py-7">
        <Outlet />
      </main>
    </div>
  );
}
