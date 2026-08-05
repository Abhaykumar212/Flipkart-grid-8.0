import { HeroCarousel } from "../components/home/HeroCarousel";
import { CategoryStrip } from "../components/home/CategoryStrip";
import { ProductRail } from "../components/home/ProductRail";
import { ForYouPersuasion } from "../components/home/ForYouPersuasion";
import { products, productsByCategory } from "../data/products";
import { discountPercent } from "../lib/format";
import { useAdminCatalog } from "../context/AdminCatalogContext";

/** Steepest discounts first — stands in for a real deals feed. */
const dealsOfTheDay = [...products]
  .sort(
    (a, b) =>
      discountPercent(b.price.mrp, b.price.sellingPrice) -
      discountPercent(a.price.mrp, a.price.sellingPrice),
  )
  .slice(0, 12);

const bestOfElectronics = productsByCategory("electronics");

export default function Home() {
  const { storeProducts } = useAdminCatalog();

  return (
    <>
      <CategoryStrip />
      <HeroCarousel />
      {/* Real personalization — reads userHistory, replaces the old static
          "highest rated across the catalog" placeholder rail entirely. */}
      <ForYouPersuasion />
      {storeProducts.length > 0 && (
        <ProductRail
          title="Just Added by Sellers"
          subtitle="Live from the catalog admin backend"
          products={storeProducts}
        />
      )}
      <ProductRail
        title="Deals of the Day"
        subtitle="Ends in 08:14:22"
        products={dealsOfTheDay}
      />
      <ProductRail
        title="Best of Electronics"
        subtitle="Laptops & Televisions"
        products={bestOfElectronics}
      />
    </>
  );
}
