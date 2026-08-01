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

/** Secondary text nav below the blue header. */
export const navCategories: { label: string; hasDropdown: boolean }[] = [
  { label: "Grocery", hasDropdown: false },
  { label: "Mobiles", hasDropdown: false },
  { label: "Fashion", hasDropdown: true },
  { label: "Electronics", hasDropdown: true },
  { label: "Home & Furniture", hasDropdown: true },
  { label: "Appliances", hasDropdown: false },
  { label: "Flight Bookings", hasDropdown: false },
  { label: "Beauty, Toys & More", hasDropdown: true },
  { label: "Two Wheelers", hasDropdown: true },
];

/** Circular icon strip on the homepage. */
export interface HomeCategory {
  label: string;
  icon: LucideIcon;
  tint: string;
}

export const homeCategories: HomeCategory[] = [
  { label: "Grocery", icon: ShoppingBasket, tint: "bg-green-50 text-green-600" },
  { label: "Mobiles", icon: Smartphone, tint: "bg-blue-50 text-blue-600" },
  { label: "Fashion", icon: Shirt, tint: "bg-pink-50 text-pink-600" },
  { label: "Electronics", icon: Laptop, tint: "bg-indigo-50 text-indigo-600" },
  { label: "Home", icon: Home, tint: "bg-amber-50 text-amber-600" },
  { label: "Appliances", icon: WashingMachine, tint: "bg-cyan-50 text-cyan-600" },
  { label: "Beauty", icon: Sparkles, tint: "bg-rose-50 text-rose-600" },
  { label: "Audio", icon: Headphones, tint: "bg-violet-50 text-violet-600" },
  { label: "Furniture", icon: Armchair, tint: "bg-orange-50 text-orange-600" },
  { label: "Two Wheelers", icon: Bike, tint: "bg-slate-100 text-slate-600" },
];
