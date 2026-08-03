import { Activity, BarChart3, FlaskConical, ExternalLink, RadioTower } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-5 py-3 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-400 text-slate-950"><RadioTower className="h-5 w-5" /></span>
            <div><p className="text-sm font-bold tracking-tight">Decision Intelligence</p><p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Flipkart GRiD · Live operations</p></div>
          </div>
          <nav className="flex items-center gap-2 text-xs">
            <NavLink end to="/dashboard" className={({ isActive }) => `inline-flex items-center gap-1.5 rounded-lg px-3 py-2 ${isActive ? "bg-slate-800 text-cyan-300" : "text-slate-400 hover:text-white"}`}><Activity className="h-3.5 w-3.5" />Live sessions</NavLink>
            <NavLink to="/dashboard/metrics" className={({ isActive }) => `inline-flex items-center gap-1.5 rounded-lg px-3 py-2 ${isActive ? "bg-slate-800 text-cyan-300" : "text-slate-400 hover:text-white"}`}><BarChart3 className="h-3.5 w-3.5" />Models</NavLink>
            <NavLink to="/dashboard/experiments" className={({ isActive }) => `inline-flex items-center gap-1.5 rounded-lg px-3 py-2 ${isActive ? "bg-slate-800 text-cyan-300" : "text-slate-400 hover:text-white"}`}><FlaskConical className="h-3.5 w-3.5" />Experiments</NavLink>
            <Link to="/" className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-slate-400 hover:text-white">Storefront<ExternalLink className="h-3.5 w-3.5" /></Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1600px] px-5 py-7 lg:px-8 lg:py-9"><Outlet /></main>
    </div>
  );
}
