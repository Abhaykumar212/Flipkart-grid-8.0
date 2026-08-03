import type { Product } from "../../types/product";
import { ProductRail } from "../home/ProductRail";
import { 
  getSimilarProducts, 
  getBrandProducts, 
  getBudgetAlternatives, 
  getRecentlyViewed, 
  getCrossCategoryProducts 
} from "../../lib/relatedProducts";

interface RelatedProductsRailProps {
  product: Product;
}

export function RelatedProductsRail({ product }: RelatedProductsRailProps) {
  const similarProducts = getSimilarProducts(product);
  const brandProducts = getBrandProducts(product);
  const budgetAlternatives = getBudgetAlternatives(product);
  const crossCategoryProducts = getCrossCategoryProducts(product);
  const recentlyViewed = getRecentlyViewed(product.id);

  return (
    <>
      {similarProducts.length > 0 && (
        <ProductRail
          title="Similar Products"
          subtitle="Based on this product's category"
          products={similarProducts}
        />
      )}
      
      {brandProducts.length > 0 && (
        <ProductRail
          title={`More from ${product.brand}`}
          subtitle="Explore the brand"
          products={brandProducts}
        />
      )}

      {budgetAlternatives.length > 0 && (
        <ProductRail
          title="Budget Alternatives"
          subtitle="Save more on similar items"
          products={budgetAlternatives}
        />
      )}

      {crossCategoryProducts.length > 0 && (
        <ProductRail
          title="You may also like"
          subtitle={`From ${product.category}`}
          products={crossCategoryProducts}
        />
      )}

      {recentlyViewed.length > 0 && (
        <ProductRail
          title="Recently Viewed"
          subtitle="Your browsing history"
          products={recentlyViewed}
        />
      )}
    </>
  );
}
