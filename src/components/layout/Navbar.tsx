import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bell,
  ChevronDown,
  Download,
  Heart,
  HelpCircle,
  Search,
  ShoppingCart,
  Store,
  TrendingUp,
  User,
} from "lucide-react";
import { Logo } from "./Logo";
import { useCart } from "../../context/CartContext";
import { useWishlist } from "../../context/WishlistContext";
import { useSession } from "../../context/SessionContext";
import { products } from "../../data/products";
import { formatINR } from "../../lib/format";

const accountMenu = [
  { label: "My Profile", icon: User, href: "https://www.flipkart.com/account/login" },
  { label: "Orders", icon: ShoppingCart, href: "https://www.flipkart.com/account/orders" },
  { label: "Wishlist", icon: Heart, to: "/wishlist" },
  { label: "Flipkart Plus Zone", icon: TrendingUp, href: "https://www.flipkart.com/plus" },
];

const moreMenu = [
  { label: "Notification Preferences", icon: Bell, href: "https://www.flipkart.com/communication-preferences/push" },
  { label: "24x7 Customer Care", icon: HelpCircle, href: "https://www.flipkart.com/helpcentre" },
  { label: "Advertise", icon: TrendingUp, href: "https://advertising.flipkart.com" },
  { label: "Download App", icon: Download, href: "https://www.flipkart.com/mobile-apps" },
];

interface MenuItem {
  label: string;
  icon: typeof User;
  to?: string;
  href?: string;
}

function Dropdown({ items, className = "" }: { items: MenuItem[]; className?: string }) {
  return (
    <div className={`absolute top-full z-50 hidden w-60 pt-3 group-hover:block group-focus-within:block ${className}`}>
      <div className="rounded-[2px] bg-white py-1 shadow-[0_4px_16px_rgba(0,0,0,0.2)]">
        {items.map(({ label, icon: Icon, to, href }) => {
          const content = <><Icon className="h-4 w-4 text-fk-blue" strokeWidth={2} />{label}</>;
          const classes = "flex min-h-11 w-full items-center gap-3 border-b border-fk-border/60 px-4 py-2.5 text-left text-fk-md text-fk-ink last:border-0 hover:bg-fk-bg";
          return to ? <Link key={label} to={to} className={classes}>{content}</Link> : <a key={label} href={href} className={classes} target="_blank" rel="noreferrer">{content}</a>;
        })}
      </div>
    </div>
  );
}

export function Navbar() {
  const navigate = useNavigate();
  const { count } = useCart();
  const { count: wishlistCount } = useWishlist();
  const { emit } = useSession();
  const [query, setQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);

  const suggestions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (normalized.length < 2) return [];
    return products
      .filter((product) => `${product.title} ${product.brand} ${product.subCategory}`.toLowerCase().includes(normalized))
      .slice(0, 6);
  }, [query]);

  const recordSearch = (value: string) => {
    const normalized = value.trim();
    if (!normalized) return false;
    const resultCount = products.filter((product) => (
      `${product.title} ${product.brand} ${product.subCategory}`
        .toLowerCase()
        .includes(normalized.toLowerCase())
    )).length;
    emit("SEARCH_PERFORMED", {
      metadata: { query: normalized, result_count: resultCount, sort_order: "RELEVANCE" },
    });
    return true;
  };

  const runSearch = (value: string) => {
    const normalized = value.trim();
    if (!recordSearch(normalized)) return;
    setSearchFocused(false);
    navigate(`/products?q=${encodeURIComponent(normalized)}`);
  };

  return (
    <header className="sticky top-0 z-50 bg-fk-blue shadow-[0_1px_2px_0_rgba(0,0,0,0.16)]">
      <nav className="mx-auto flex max-w-fk flex-wrap items-center gap-2 px-3 py-2 sm:h-14 sm:flex-nowrap sm:px-4 sm:py-0 xl:gap-6" aria-label="Primary navigation">
        <Logo />

        <form className="relative order-3 w-full sm:order-none sm:ml-2 sm:min-w-0 sm:flex-1 xl:ml-8" onSubmit={(event) => { event.preventDefault(); runSearch(query); }} role="search">
          <input
            type="search"
            name="q"
            autoComplete="off"
            spellCheck={false}
            value={query}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search for Products, Brands and More"
            aria-label="Search for Products, Brands and More"
            aria-autocomplete="list"
            aria-controls="search-suggestions"
            className="h-11 w-full rounded-[2px] bg-white pl-4 pr-11 text-base text-fk-ink placeholder:text-fk-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue-dark sm:h-9 sm:text-fk-md"
          />
          <button type="submit" aria-label="Search" className="absolute right-0 top-0 flex h-11 w-11 items-center justify-center text-fk-blue sm:h-9">
            <Search className="h-5 w-5" strokeWidth={2.5} />
          </button>

          {searchFocused && suggestions.length > 0 && (
            <div id="search-suggestions" role="listbox" className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-[2px] bg-white shadow-[0_4px_16px_rgba(0,0,0,0.2)]">
              {suggestions.map((product) => (
                <Link key={product.id} to={`/product/${product.slug}`} role="option" aria-selected="false" onClick={() => { recordSearch(query); setSearchFocused(false); }} className="flex min-h-14 items-center gap-3 border-b border-fk-border px-3 py-2 last:border-0 hover:bg-fk-bg">
                  <img src={product.images[0]} alt="" loading="lazy" width="40" height="40" className="h-10 w-10 object-contain" />
                  <span className="min-w-0 flex-1 truncate text-fk-base text-fk-ink">{product.title}</span>
                  <span className="shrink-0 text-fk-base font-medium text-fk-ink">{formatINR(product.price.sellingPrice)}</span>
                </Link>
              ))}
              <button type="submit" className="flex min-h-11 w-full items-center gap-2 px-4 text-left text-fk-base font-medium text-fk-blue hover:bg-fk-bg">
                <Search className="h-4 w-4" /> View all results for “{query.trim()}”
              </button>
            </div>
          )}
        </form>

        <div className="group relative hidden shrink-0 md:block">
          <a href="https://www.flipkart.com/account/login" target="_blank" rel="noreferrer" className="flex h-9 items-center gap-1.5 rounded-[2px] bg-white px-7 text-fk-md font-bold text-fk-blue">
            Login <ChevronDown className="h-3.5 w-3.5 transition-transform group-hover:rotate-180" />
          </a>
          <Dropdown items={accountMenu} className="left-0" />
        </div>

        <a href="https://seller.flipkart.com" target="_blank" rel="noreferrer" className="hidden shrink-0 items-center gap-1.5 text-fk-md font-medium text-white lg:flex">
          <Store className="h-4 w-4" strokeWidth={2} /> Become a Seller
        </a>

        <div className="group relative hidden shrink-0 lg:block">
          <button type="button" className="flex min-h-11 items-center gap-1 text-fk-md font-medium text-white">
            More <ChevronDown className="h-3.5 w-3.5 transition-transform group-hover:rotate-180" />
          </button>
          <Dropdown items={moreMenu} className="right-0" />
        </div>

        <Link to="/wishlist" aria-label={`Wishlist with ${wishlistCount} items`} className="relative ml-auto flex h-11 w-11 shrink-0 items-center justify-center text-white sm:ml-0 md:hidden">
          <Heart className="h-5 w-5" />
          {wishlistCount > 0 && <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-fk-flame px-1 text-[10px] font-bold text-white">{wishlistCount > 99 ? "99+" : wishlistCount}</span>}
        </Link>

        <Link to="/cart" aria-label={`Shopping cart with ${count} items`} className="relative flex h-11 shrink-0 items-center gap-2 px-1 text-fk-md font-medium text-white">
          <span className="relative">
            <ShoppingCart className="h-5 w-5" strokeWidth={2} />
            {count > 0 && <span className="absolute -right-2 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-fk-flame px-1 text-[10px] font-bold leading-none text-white" data-testid="cart-badge" aria-live="polite">{count > 99 ? "99+" : count}</span>}
          </span>
          <span className="hidden sm:inline">Cart</span>
        </Link>
      </nav>
    </header>
  );
}
