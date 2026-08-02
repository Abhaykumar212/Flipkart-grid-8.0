import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";
import { CategoryNav } from "./CategoryNav";
import { Footer } from "./Footer";
import { AgentInspector } from "../ui/AgentInspector";
import { CompanionWidget } from "../companion/CompanionWidget";
import { InterventionProvider } from "../../context/InterventionContext";
import { InterventionRenderer } from "../intervention/InterventionRenderer";

export function Layout() {
  return (
    // InterventionProvider sits inside the router and TrackerProvider (both from
    // App.tsx) because it needs the current route and the live RCA response.
    <InterventionProvider>
      <div className="flex min-h-screen flex-col bg-fk-bg">
        <Navbar />
        <CategoryNav />
        <main className="mx-auto w-full max-w-fk flex-1 px-4 py-3">
          <Outlet />
        </main>
        <Footer />
        <AgentInspector />
        <CompanionWidget />
        <InterventionRenderer />
      </div>
    </InterventionProvider>
  );
}
