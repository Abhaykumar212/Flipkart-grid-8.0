import { productById, products } from "../data/products";
import type { Product } from "../types/product";
import type { ProductVisit } from "./shoppingContext";

function discount(product: Product): number {
  return product.price.mrp > 0
    ? (product.price.mrp - product.price.sellingPrice) / product.price.mrp
    : 0;
}

function byQualityAndValue(left: Product, right: Product): number {
  return right.rating.value - left.rating.value || discount(right) - discount(left);
}

export function comparableProducts(product: Product, limit = 3): Product[] {
  const minimum = product.price.sellingPrice * 0.6;
  const maximum = product.price.sellingPrice * 1.4;
  return products
    .filter((candidate) => (
      candidate.id !== product.id
      && candidate.subCategory === product.subCategory
      && candidate.price.sellingPrice >= minimum
      && candidate.price.sellingPrice <= maximum
    ))
    .sort(byQualityAndValue)
    .slice(0, limit);
}

export function similarProducts(product: Product, limit = 10): Product[] {
  return products
    .filter((candidate) => (
      candidate.id !== product.id && candidate.subCategory === product.subCategory
    ))
    .sort(byQualityAndValue)
    .slice(0, limit);
}

export function categoryDiscoveries(product: Product, limit = 10): Product[] {
  return products
    .filter((candidate) => (
      candidate.id !== product.id
      && candidate.category === product.category
      && candidate.subCategory !== product.subCategory
    ))
    .sort(byQualityAndValue)
    .slice(0, limit);
}

export function recentlyViewedProducts(
  history: ProductVisit[],
  currentProductId: string,
  limit = 10,
): Product[] {
  return history
    .filter((visit) => visit.productId !== currentProductId)
    .map((visit) => productById.get(visit.productId))
    .filter((product): product is Product => Boolean(product))
    .slice(0, limit);
}
