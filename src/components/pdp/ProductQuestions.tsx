import { useState } from "react";
import { MessageCircleQuestion } from "lucide-react";
import type { Product } from "../../types/product";
import { shoppingContext } from "../../lib/shoppingContext";
import { Button } from "../ui/Button";

export function ProductQuestions({ product }: { product: Product }) {
  const [question, setQuestion] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const ask = (prompt: string) => {
    const normalized = prompt.trim();
    if (!normalized) return;
    shoppingContext.requestCompanion(normalized);
    setQuestion("");
    setSubmitted(true);
  };

  return (
    <section className="rounded-[2px] bg-white p-4 sm:p-6" aria-labelledby="questions-heading">
      <div className="flex items-center gap-2">
        <MessageCircleQuestion className="h-5 w-5 text-fk-blue" aria-hidden="true" />
        <h2 id="questions-heading" className="text-fk-xl font-medium text-fk-ink">Questions about this product?</h2>
      </div>
      <p className="mt-1 text-fk-sm text-fk-muted">Get an immediate answer grounded in this listing and its review sample.</p>
      <form onSubmit={(event) => { event.preventDefault(); ask(question); }} className="mt-4 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="product-question" className="sr-only">Question about {product.title}</label>
        <input
          id="product-question"
          value={question}
          onChange={(event) => { setQuestion(event.target.value); setSubmitted(false); }}
          placeholder="Ask about delivery, EMI, specifications, or reviews"
          className="h-11 min-w-0 flex-1 border border-fk-border px-3 text-base focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue"
        />
        <Button type="submit" disabled={!question.trim()} className="min-h-11">Ask companion</Button>
      </form>
      {submitted && <p className="mt-2 text-fk-sm text-fk-green" role="status">Your grounded answer is open in the shopping companion.</p>}
    </section>
  );
}
