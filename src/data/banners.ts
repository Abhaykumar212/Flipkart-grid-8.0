export interface Banner {
  id: string;
  headline: string;
  sub: string;
  cta: string;
  href: string;
  /** Tailwind gradient classes — self-contained, no external banner assets. */
  gradient: string;
  accent: string;
}

export const banners: Banner[] = [
  {
    id: "b-1",
    headline: "Big Saving Days",
    sub: "Up to 80% off across Electronics, Fashion & Home",
    cta: "Shop Now",
    href: "/products?sort=discount",
    gradient: "from-[#2874f0] via-[#1e5fc4] to-[#0d3d8c]",
    accent: "text-fk-yellow",
  },
  {
    id: "b-2",
    headline: "Flat 15% Off on Flight Bookings",
    sub: "Flash Sale · 2-3 PM | 8-9 PM | 10 PM-12 AM",
    cta: "Book Now",
    href: "https://www.flipkart.com/travel/flights",
    gradient: "from-[#0b7ec4] via-[#0a9bd6] to-[#48c6ef]",
    accent: "text-white",
  },
  {
    id: "b-3",
    headline: "Best of Smartphones",
    sub: "No Cost EMI from ₹1,400/month · Exchange up to ₹55,000 off",
    cta: "Explore",
    href: "/category/mobiles",
    gradient: "from-[#1a1a2e] via-[#2d1b4e] to-[#4a1f6e]",
    accent: "text-fk-yellow",
  },
  {
    id: "b-4",
    headline: "₹0 Platform Fee",
    sub: "Everything in Minutes · Deals from ₹1",
    cta: "Order Now",
    href: "/products?sort=price-asc",
    gradient: "from-[#0f9d58] via-[#1cb45f] to-[#7ed957]",
    accent: "text-white",
  },
];
