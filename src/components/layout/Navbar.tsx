import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ChevronDown,
  Search,
  ShoppingCart,
  Store,
  User,
  Bell,
  HelpCircle,
  TrendingUp,
  Download,
} from "lucide-react";
import { Logo } from "./Logo";
import { useCart } from "../../context/CartContext";
import { useTracker } from "../../context/TrackerContext";

const accountMenu = [
  { label: "My Profile", icon: User },
  { label: "Flipkart Plus Zone", icon: TrendingUp },
  { label: "Orders", icon: ShoppingCart },
  { label: "Wishlist", icon: Bell },
  { label: "Rewards", icon: TrendingUp },
  { label: "Gift Cards", icon: Store },
];

const moreMenu = [
  { label: "Notification Preferences", icon: Bell },
  { label: "24x7 Customer Care", icon: HelpCircle },
  { label: "Advertise", icon: TrendingUp },
  { label: "Download App", icon: Download },
];

interface DropdownProps {
  items: { label: string; icon: typeof User }[];
  className?: string;
}

function Dropdown({ items, className = "" }: DropdownProps) {
  return (
    <div
      className={`absolute top-full z-50 hidden w-60 pt-3 group-hover:block ${className}`}
    >
      <div className="rounded-[2px] bg-white py-1 shadow-[0_4px_16px_rgba(0,0,0,0.2)]">
        <span className="absolute -top-0 left-8 h-3 w-3 rotate-45 bg-white" />
        {items.map(({ label, icon: Icon }) => (
          <button
            key={label}
            className="flex w-full items-center gap-3 border-b border-fk-border/60 px-4 py-2.5 text-left text-fk-md text-fk-ink last:border-0 hover:bg-fk-bg"
          >
            <Icon className="h-4 w-4 text-fk-blue" strokeWidth={2} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Navbar() {
  const { count } = useCart();
  const { recordSearch } = useTracker();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      recordSearch(trimmed);
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-fk-blue shadow-[0_1px_2px_0_rgba(0,0,0,0.16)]">
      <nav className="mx-auto flex h-14 max-w-fk items-center gap-2 px-4 xl:gap-6">
        <Logo />

        {/* Search */}
        <form
          className="relative ml-2 min-w-0 flex-1 xl:ml-8"
          onSubmit={handleSearchSubmit}
          role="search"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for Products, Brands and More"
            aria-label="Search for Products, Brands and More"
            className="h-9 w-full rounded-[2px] bg-white pl-4 pr-11 text-fk-md text-fk-ink placeholder:text-fk-muted focus:outline-none"
          />
          <button
            type="submit"
            aria-label="Search"
            className="absolute right-0 top-0 flex h-9 w-11 items-center justify-center text-fk-blue"
          >
            <Search className="h-4.5 w-4.5" strokeWidth={2.5} />
          </button>
        </form>

        {/* Login + account dropdown */}
        <div className="group relative shrink-0">
          <button className="flex h-9 items-center gap-1.5 rounded-[2px] bg-white px-8 text-fk-md font-bold text-fk-blue">
            Login
            <ChevronDown className="h-3.5 w-3.5 transition-transform group-hover:rotate-180" />
          </button>
          <Dropdown items={accountMenu} className="left-0" />
        </div>

        <Link
          to="#"
          className="hidden shrink-0 items-center gap-1.5 text-fk-md font-medium text-white lg:flex"
        >
          <Store className="h-4 w-4" strokeWidth={2} />
          Become a Seller
        </Link>

        {/* More dropdown */}
        <div className="group relative hidden shrink-0 lg:block">
          <button className="flex items-center gap-1 text-fk-md font-medium text-white">
            More
            <ChevronDown className="h-3.5 w-3.5 transition-transform group-hover:rotate-180" />
          </button>
          <Dropdown items={moreMenu} className="right-0" />
        </div>

        <Link
          to="/cart"
          className="relative flex shrink-0 items-center gap-2 text-fk-md font-medium text-white"
        >
          <span className="relative">
            <ShoppingCart className="h-5 w-5" strokeWidth={2} />
            {count > 0 && (
              <span
                className="absolute -right-2 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-fk-flame px-1 text-[10px] font-bold leading-none text-white"
                data-testid="cart-badge"
              >
                {count}
              </span>
            )}
          </span>
          <span className="hidden sm:inline">Cart</span>
        </Link>
      </nav>
    </header>
  );
}
