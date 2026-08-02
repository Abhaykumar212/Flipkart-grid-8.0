import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";
import { CategoryNav } from "./CategoryNav";
import { Footer } from "./Footer";
import { AgentInspector } from "../ui/AgentInspector";
import { InterventionRenderer } from "../intervention/InterventionRenderer";

export function Layout() {
  return (
    <div className="flex min-h-screen min-w-0 flex-col bg-fk-bg">
      <a href="#main-content" className="fixed left-3 top-3 z-[100] -translate-y-20 rounded-[2px] bg-white px-4 py-3 text-fk-md font-medium text-fk-blue shadow-fk-hover focus:translate-y-0">
        Skip to content
      </a>
      <Navbar />
      <CategoryNav />
      <InterventionRenderer surface="global" />
      <main id="main-content" className="mx-auto w-full max-w-fk min-w-0 scroll-mt-28 flex-1 px-2 py-3 sm:px-4">
        <Outlet />
      </main>
      <Footer />
      <AgentInspector />
    </div>
  );
}
