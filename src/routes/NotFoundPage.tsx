import { SearchX } from "lucide-react";
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="flex min-h-[480px] flex-col items-center justify-center bg-white px-6 py-16 text-center">
      <SearchX className="h-16 w-16 text-fk-border" strokeWidth={1.5} />
      <h1 className="mt-4 text-2xl font-medium text-fk-ink">We couldn’t find that page</h1>
      <p className="mt-2 text-fk-base text-fk-muted">The link may be outdated, but the complete catalog is ready to browse.</p>
      <Link to="/products" className="mt-5 inline-flex min-h-12 items-center rounded-[2px] bg-fk-blue px-7 text-fk-md font-medium uppercase text-white hover:bg-fk-blue-dark">Browse Products</Link>
    </section>
  );
}
