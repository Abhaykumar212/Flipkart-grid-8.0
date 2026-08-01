import {
  Smartphone,
  Laptop,
  Shirt,
  WashingMachine,
  Headphones,
  LayoutGrid,
  type LucideIcon,
} from "lucide-react";
import type { CategorySlug } from "../types/product";

export interface CatalogCategory {
  slug: CategorySlug;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
  tint: string;
  subcategories: string[];
}

/**
 * Store taxonomy for the 50-product demo catalog. Navigation components consume
 * this single collection so desktop, mobile, homepage, and footer stay aligned.
 */
export const catalogCategories: CatalogCategory[] = [
  {
    slug: "mobiles",
    label: "Mobiles & Tablets",
    shortLabel: "Mobiles",
    description: "Smartphones, 5G devices and everyday mobile essentials",
    icon: Smartphone,
    tint: "bg-blue-50 text-blue-600",
    subcategories: ["Smartphones"],
  },
  {
    slug: "electronics",
    label: "Electronics",
    shortLabel: "Electronics",
    description: "Laptops, gaming machines and smart televisions",
    icon: Laptop,
    tint: "bg-indigo-50 text-indigo-600",
    subcategories: ["Gaming Laptops", "Thin and Light Laptops", "Televisions"],
  },
  {
    slug: "fashion",
    label: "Fashion",
    shortLabel: "Fashion",
    description: "Footwear, clothing and bags for every day",
    icon: Shirt,
    tint: "bg-pink-50 text-pink-600",
    subcategories: ["Casual Shoes", "Sports Shoes", "T-Shirts", "Jeans", "Formal Shirts", "Bags & Backpacks", "Kurtas"],
  },
  {
    slug: "appliances",
    label: "Home Appliances",
    shortLabel: "Appliances",
    description: "Large and small appliances for a smarter home",
    icon: WashingMachine,
    tint: "bg-cyan-50 text-cyan-600",
    subcategories: ["Refrigerators", "Washing Machines", "Kitchen Appliances", "Air Conditioners"],
  },
  {
    slug: "audio",
    label: "Audio",
    shortLabel: "Audio",
    description: "Earbuds, headphones and neckbands",
    icon: Headphones,
    tint: "bg-violet-50 text-violet-600",
    subcategories: ["True Wireless Earbuds", "Headphones", "Neckbands"],
  },
];

export const categoryBySlug = new Map(catalogCategories.map((category) => [category.slug, category]));

export const navCategories = catalogCategories.map((category) => ({
  label: category.shortLabel,
  slug: category.slug,
  hasDropdown: category.subcategories.length > 1,
}));

export const homeCategories = [
  {
    label: "All Products",
    slug: null,
    icon: LayoutGrid,
    tint: "bg-slate-100 text-slate-600",
  },
  ...catalogCategories.map(({ shortLabel: label, slug, icon, tint }) => ({
    label,
    slug,
    icon,
    tint,
  })),
];
