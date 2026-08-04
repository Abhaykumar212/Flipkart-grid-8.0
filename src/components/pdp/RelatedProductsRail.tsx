import { useSyncExternalStore } from "react";
import type { Product } from "../../types/product";
import {
  categoryDiscoveries,
  recentlyViewedProducts,
  similarProducts,
} from "../../lib/productRecommendations";
import { shoppingContext } from "../../lib/shoppingContext";
import { ProductRail } from "../home/ProductRail";

export function RelatedProductsRail({ product }: { product: Product }) {
  const context = useSyncExternalStore(
    shoppingContext.subscribe,
    shoppingContext.getSnapshot,
    shoppingContext.getSnapshot,
  );
  const similar = similarProducts(product);
  const discoveries = categoryDiscoveries(product);
  const recent = recentlyViewedProducts(context.visitHistory, product.id);

  return (
    <>
      {similar.length > 0 && (
        <ProductRail
          title="Similar products"
          subtitle={`More in ${product.subCategory}`}
          products={similar}
          viewAllHref={`/category/${product.category}`}
          originProductId={product.id}
        />
      )}
      {discoveries.length > 0 && (
        <ProductRail
          title="You may also like"
          subtitle={`Popular picks across ${product.category}`}
          products={discoveries}
          viewAllHref={`/category/${product.category}`}
          originProductId={product.id}
        />
      )}
      {recent.length > 0 && (
        <ProductRail
          title="Recently viewed"
          subtitle="From this browsing session"
          products={recent}
          originProductId={product.id}
        />
      )}
    </>
  );
}
