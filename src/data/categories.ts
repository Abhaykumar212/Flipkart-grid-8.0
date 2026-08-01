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
  type LucideIcon,
} from "lucide-react";
import type { CategorySlug } from "../types/product";

/**
 * `categorySlug` maps a nav label onto the catalog's real `CategorySlug` where
 * one exists. Labels with no matching inventory (Grocery, Flight Bookings, ...)
 * are still clickable — the search results page just shows an honest "no
 * products yet" state for them rather than pretending to have stock.
 */
export interface NavCategory {
  label: string;
  hasDropdown: boolean;
  categorySlug: CategorySlug | null;
}

/** Secondary text nav below the blue header. */
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

/** Circular icon strip on the homepage. */
export interface HomeCategory {
  label: string;
  icon: LucideIcon;
  tint: string;
  categorySlug: CategorySlug | null;
}

export const homeCategories: HomeCategory[] = [
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
