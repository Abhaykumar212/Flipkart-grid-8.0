import {
  Smartphone,
  Laptop,
  Shirt,
  Home,
  WashingMachine,
  Sparkles,
  ShoppingBasket,
  Headphones,
  Armchair,
  Bike,
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

/** Store taxonomy for the 50-product catalog and its filter pages. */
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

/** Flipkart-style labels map to real inventory where the catalog has a match. */
export interface NavCategory {
  label: string;
  hasDropdown: boolean;
  categorySlug: CategorySlug | null;
}

export const navCategories: NavCategory[] = [
  { label: "Grocery", hasDropdown: false, categorySlug: null },
  { label: "Mobiles", hasDropdown: false, categorySlug: "mobiles" },
  { label: "Fashion", hasDropdown: true, categorySlug: "fashion" },
  { label: "Electronics", hasDropdown: true, categorySlug: "electronics" },
  { label: "Home & Furniture", hasDropdown: true, categorySlug: null },
  { label: "Appliances", hasDropdown: false, categorySlug: "appliances" },
  { label: "Flight Bookings", hasDropdown: false, categorySlug: null },
  { label: "Beauty, Toys & More", hasDropdown: true, categorySlug: null },
  { label: "Two Wheelers", hasDropdown: true, categorySlug: null },
];

export interface HomeCategory {
  label: string;
  icon: LucideIcon;
  tint: string;
  categorySlug: CategorySlug | null;
}

export const homeCategories: HomeCategory[] = [
  { label: "All Products", icon: LayoutGrid, tint: "bg-slate-100 text-slate-600", categorySlug: null },
  { label: "Grocery", icon: ShoppingBasket, tint: "bg-green-50 text-green-600", categorySlug: null },
  { label: "Mobiles", icon: Smartphone, tint: "bg-blue-50 text-blue-600", categorySlug: "mobiles" },
  { label: "Fashion", icon: Shirt, tint: "bg-pink-50 text-pink-600", categorySlug: "fashion" },
  { label: "Electronics", icon: Laptop, tint: "bg-indigo-50 text-indigo-600", categorySlug: "electronics" },
  { label: "Home", icon: Home, tint: "bg-amber-50 text-amber-600", categorySlug: null },
  { label: "Appliances", icon: WashingMachine, tint: "bg-cyan-50 text-cyan-600", categorySlug: "appliances" },
  { label: "Beauty", icon: Sparkles, tint: "bg-rose-50 text-rose-600", categorySlug: null },
  { label: "Audio", icon: Headphones, tint: "bg-violet-50 text-violet-600", categorySlug: "audio" },
  { label: "Furniture", icon: Armchair, tint: "bg-orange-50 text-orange-600", categorySlug: null },
  { label: "Two Wheelers", icon: Bike, tint: "bg-slate-100 text-slate-600", categorySlug: null },
];
