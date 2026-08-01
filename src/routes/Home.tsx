import { HeroCarousel } from "../components/home/HeroCarousel";
import { CategoryStrip } from "../components/home/CategoryStrip";
import { ProductRail } from "../components/home/ProductRail";
import { products, productsByCategory } from "../data/products";
import { discountPercent } from "../lib/format";

/** Steepest discounts first — stands in for a real deals feed. */
const dealsOfTheDay = [...products]
  .sort(
    (a, b) =>
      discountPercent(b.price.mrp, b.price.sellingPrice) -
      discountPercent(a.price.mrp, a.price.sellingPrice),
  )
  .slice(0, 12);

const bestOfElectronics = productsByCategory("electronics");

/** Highest-rated across the catalog — the slot the agent will later personalise. */
const suggestedForYou = [...products]
  .sort((a, b) => b.rating.value - a.rating.value)
  .slice(0, 12);

export default function Home() {
  return (
    <>
      <CategoryStrip />
      <HeroCarousel />
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
      <ProductRail
        title="Suggested for You"
        subtitle="Based on your activity"
        products={suggestedForYou}
      />
    </>
  );
}
