import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";
import { CategoryNav } from "./CategoryNav";
import { Footer } from "./Footer";

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-fk-bg">
      <Navbar />
      <CategoryNav />
      <main className="mx-auto w-full max-w-fk flex-1 px-4 py-3">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
