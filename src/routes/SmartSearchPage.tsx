import { useState } from "react";
import { Link } from "react-router-dom";
import { Search, Sparkles, Loader2 } from "lucide-react";
import { productById } from "../data/products";

interface RagResult {
  product_id: string;
  title: string;
  score: number;
  snippet: string;
  field: string;
}

const FIELD_LABEL: Record<string, string> = {
  listing: "Listing",
  description: "Description",
  highlight: "Highlight",
  specification: "Specification",
  review: "Customer review",
};

const EXAMPLES = [
  "phone with great battery life",
  "laptop good for gaming",
  "budget headphones with noise cancellation",
  "durable and easy to clean",
];

/**
 * True RAG / vector retrieval — a real TF-IDF vector index over the catalog
 * (`backend/agents/retrieval.py`), queried via cosine similarity, not a
 * keyword `.includes()` filter. Distinct from the companion widget's
 * single-product chat (which deliberately doesn't need retrieval — see that
 * module's docstring): this searches across the whole catalog and shows the
 * actual retrieved passage + similarity score, so the retrieval step itself
 * is visible, not hidden behind a chat reply.
 */
export default function SmartSearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RagResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [indexed, setIndexed] = useState(true);

  const runSearch = async (q: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/rag-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, k: 8 }),
      });
      const data = await response.json();
      setIndexed(Boolean(data.indexed));
      setResults(data.results ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="bg-white p-4 sm:p-6">
        <h1 className="flex items-center gap-2 text-fk-lg font-semibold text-fk-ink">
          <Sparkles className="h-5 w-5 text-fk-blue" /> Smart Search (Vector Retrieval)
        </h1>
        <p className="mt-1 text-fk-sm text-fk-muted">
          Searches product descriptions, specs and reviews by meaning, not exact keywords — a real
          TF-IDF vector index with cosine similarity (<code>backend/agents/retrieval.py</code>).
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void runSearch(query);
          }}
          className="mt-4 flex gap-2"
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Try "phone with great battery life"'
            className="flex-1 rounded border border-fk-border px-4 py-2.5 text-fk-md outline-none focus:border-fk-blue"
            data-testid="smart-search-input"
          />
          <button
            type="submit"
            className="flex items-center gap-2 rounded bg-fk-blue px-5 py-2.5 text-fk-md font-medium text-white"
            data-testid="smart-search-submit"
          >
            <Search size={16} /> Search
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => void runSearch(ex)}
              className="rounded-full border border-fk-border px-3 py-1 text-fk-xs text-fk-muted hover:border-fk-blue hover:text-fk-blue"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 bg-white p-8 text-fk-muted">
          <Loader2 className="h-5 w-5 animate-spin" /> Retrieving…
        </div>
      )}

      {!loading && results && !indexed && (
        <div className="bg-white p-6 text-center text-fk-sm text-fk-muted">
          Retrieval index not built yet — run <code>node scripts/export-catalog.mjs</code> and restart the backend.
        </div>
      )}

      {!loading && results && indexed && results.length === 0 && (
        <div className="bg-white p-6 text-center text-fk-sm text-fk-muted">No matches found for "{query}".</div>
      )}

      {!loading && results && results.length > 0 && (
        <div className="flex flex-col gap-2">
          {results.map((r, i) => {
            const product = productById.get(r.product_id);
            return (
              <div key={`${r.product_id}-${i}`} className="bg-white p-4 sm:p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    {product ? (
                      <Link to={`/product/${product.slug}`} className="text-fk-md font-medium text-fk-blue hover:underline">
                        {r.title}
                      </Link>
                    ) : (
                      <p className="text-fk-md font-medium text-fk-ink">{r.title}</p>
                    )}
                    <p className="mt-1 text-fk-xs uppercase tracking-wide text-fk-muted">
                      {FIELD_LABEL[r.field] ?? r.field}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full bg-blue-50 px-2.5 py-1 text-fk-xs font-semibold text-fk-blue">
                    {(r.score * 100).toFixed(0)}% match
                  </span>
                </div>
                <p className="mt-2 text-fk-sm text-fk-ink">"{r.snippet}"</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
