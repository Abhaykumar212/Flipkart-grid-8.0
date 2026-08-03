import type { Product } from '../types/product';
import { products, productById } from '../data/products';
import { userHistory } from './userHistory';

// Returns products in the same subcategory, excluding current product, sorted by rating
export function getSimilarProducts(product: Product, limit = 12): Product[] {
  return products
    .filter((p) => p.subCategory === product.subCategory && p.id !== product.id)
    .sort((a, b) => {
      // sort smartly (by rating desc, then by discount desc as tiebreaker)
      if (b.rating.value !== a.rating.value) {
        return b.rating.value - a.rating.value;
      }
      const getDiscount = (p: Product) => ((p.price.mrp - p.price.sellingPrice) / p.price.mrp) * 100;
      return getDiscount(b) - getDiscount(a);
    })
    .slice(0, limit);
}

// Returns products in the same subcategory within ±40% price range, for comparison
export function getCompareProducts(product: Product, limit = 4): Product[] {
  const minPrice = product.price.sellingPrice * 0.6;
  const maxPrice = product.price.sellingPrice * 1.4;

  return products
    .filter((p) => p.subCategory === product.subCategory && p.id !== product.id)
    .filter((p) => p.price.sellingPrice >= minPrice && p.price.sellingPrice <= maxPrice)
    .sort((a, b) => {
      if (b.rating.value !== a.rating.value) {
        return b.rating.value - a.rating.value;
      }
      const getDiscount = (p: Product) => ((p.price.mrp - p.price.sellingPrice) / p.price.mrp) * 100;
      return getDiscount(b) - getDiscount(a);
    })
    .slice(0, limit);
}

// Returns products from same brand, excluding current product
export function getBrandProducts(product: Product, limit = 12): Product[] {
  return products
    .filter((p) => p.brand === product.brand && p.id !== product.id)
    .slice(0, limit);
}

// Returns cheaper products in same subcategory, sorted by value (discount% * rating)
export function getBudgetAlternatives(product: Product, limit = 12): Product[] {
  return products
    .filter((p) => p.subCategory === product.subCategory && p.id !== product.id && p.price.sellingPrice < product.price.sellingPrice)
    .sort((a, b) => {
      const getDiscount = (p: Product) => ((p.price.mrp - p.price.sellingPrice) / p.price.mrp) * 100;
      const valueA = getDiscount(a) * a.rating.value;
      const valueB = getDiscount(b) * b.rating.value;
      return valueB - valueA;
    })
    .slice(0, limit);
}

// Returns recently viewed products from userHistory, mapped to Product objects
export function getRecentlyViewed(excludeId?: string, limit = 12): Product[] {
  const recentIds = userHistory.getRecentlyViewedIds(limit + (excludeId ? 1 : 0));
  const recentProducts: Product[] = [];
  
  for (const id of recentIds) {
    if (id === excludeId) continue;
    const p = productById.get(id);
    if (p) {
      recentProducts.push(p);
    }
    if (recentProducts.length >= limit) break;
  }
  
  return recentProducts;
}

// Returns products from same category but different subcategory (cross-sell)
export function getCrossCategoryProducts(product: Product, limit = 12): Product[] {
  return products
    .filter((p) => p.category === product.category && p.subCategory !== product.subCategory)
    .slice(0, limit);
}
