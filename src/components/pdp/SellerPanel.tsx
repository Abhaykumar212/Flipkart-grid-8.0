import { Clock3, Truck } from "lucide-react";
import type { Delivery, Seller } from "../../types/product";
import { RatingStars } from "../ui/RatingStars";

export function SellerPanel({ seller, delivery }: { seller: Seller; delivery: Delivery }) {
  return (
    <section className="mt-4 border-t border-fk-border pt-4" aria-labelledby="seller-heading">
      <h2 id="seller-heading" className="text-fk-sm font-medium uppercase tracking-wide text-fk-muted">Seller</h2>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <strong className="text-fk-base font-medium text-fk-blue">{seller.name}</strong>
        <RatingStars value={seller.rating} variant="pill" size="sm" />
      </div>
      <div className="mt-3 grid gap-2 text-fk-sm text-fk-ink sm:grid-cols-2">
        <span className="flex items-center gap-2"><Truck className="h-4 w-4 text-fk-blue" aria-hidden="true" />{delivery.free ? "Free delivery" : "Delivery charges apply"}</span>
        <span className="flex items-center gap-2"><Clock3 className="h-4 w-4 text-fk-blue" aria-hidden="true" />Listed delivery estimate: {delivery.estimatedDays} day{delivery.estimatedDays === 1 ? "" : "s"}</span>
        {delivery.express && <span className="flex items-center gap-2"><Truck className="h-4 w-4 text-fk-blue" aria-hidden="true" />Express delivery eligible</span>}
      </div>
    </section>
  );
}
