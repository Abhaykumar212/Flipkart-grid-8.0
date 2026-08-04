import type { Stock } from "../../types/product";

export function StockStatus({ stock }: { stock: Stock }) {
  if (!stock.inStock) {
    return (
      <p className="mt-3 border-l-4 border-fk-flame bg-red-50 px-3 py-2 text-fk-base font-medium text-fk-flame" role="status">
        Currently unavailable
      </p>
    );
  }
  if (stock.quantityLeft <= 10) {
    return (
      <p className="mt-3 inline-flex items-center gap-2 text-fk-base font-medium text-amber-700" role="status">
        <span className="h-2.5 w-2.5 rounded-full bg-amber-500 motion-safe:animate-pulse" aria-hidden="true" />
        Only {stock.quantityLeft} left in stock
      </p>
    );
  }
  return <p className="mt-3 text-fk-base font-medium text-fk-green" role="status">In stock</p>;
}
