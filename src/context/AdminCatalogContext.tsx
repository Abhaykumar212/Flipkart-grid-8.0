import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { CategorySlug, Product } from "../types/product";

/**
 * Production product/catalog backend — a real SQLite-backed store
 * (`backend/main.py`'s `/api/catalog/products` CRUD, `admin_products` table)
 * an admin actually writes to, merged into the storefront alongside (not
 * replacing) the hand-authored `src/data/products.ts`. See that file's
 * header comment for why the 50-product demo catalog stays static.
 */

export interface AdminProduct {
  id: string;
  title: string;
  brand: string;
  category: string;
  mrp: number;
  selling_price: number;
  image_url: string;
  stock_qty: number;
  description: string;
  created_at: number;
  updated_at: number;
}

const KNOWN_CATEGORIES: CategorySlug[] = ["mobiles", "electronics", "audio", "appliances", "fashion"];

/** Maps an admin-authored row onto the frontend's `Product` shape so it can
 * flow through the exact same `ProductCard`/`ProductRail`/PDP components as
 * the static catalog — no parallel rendering path to keep in sync. */
export function adminToProduct(admin: AdminProduct): Product {
  const category: CategorySlug = KNOWN_CATEGORIES.includes(admin.category as CategorySlug)
    ? (admin.category as CategorySlug)
    : "electronics";
  return {
    id: admin.id,
    slug: admin.id,
    title: admin.title,
    brand: admin.brand || "Generic",
    category,
    subCategory: admin.category,
    images: [admin.image_url || "https://rukminim2.flixcart.com/image/416/416/xif0q/cellphone/placeholder.png"],
    price: { mrp: admin.mrp, sellingPrice: admin.selling_price, currency: "INR" },
    rating: { value: 4.0, count: 0, reviewCount: 0 },
    badges: { assured: false, bestseller: false, sponsored: false },
    delivery: { free: admin.selling_price >= 500, estimatedDays: 4, express: false },
    offers: [],
    stock: { inStock: admin.stock_qty > 0, quantityLeft: admin.stock_qty },
    highlights: admin.description ? [admin.description] : [],
    description: admin.description,
  };
}

interface AdminCatalogContextValue {
  adminProducts: AdminProduct[];
  storeProducts: Product[];
  loading: boolean;
  refresh: () => Promise<void>;
  create: (input: Omit<AdminProduct, "id" | "created_at" | "updated_at">) => Promise<void>;
  update: (id: string, input: Omit<AdminProduct, "id" | "created_at" | "updated_at">) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

const AdminCatalogContext = createContext<AdminCatalogContextValue | null>(null);
const BASE = "http://localhost:8000/api/catalog/products";

export function AdminCatalogProvider({ children }: { children: ReactNode }) {
  const [adminProducts, setAdminProducts] = useState<AdminProduct[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(BASE);
      const data = await response.json();
      setAdminProducts(data.products ?? []);
    } catch {
      // Backend down or unreachable — the storefront still works with the
      // static catalog; the admin rail just stays empty.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = useCallback(
    async (input: Omit<AdminProduct, "id" | "created_at" | "updated_at">) => {
      await fetch(BASE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      await refresh();
    },
    [refresh],
  );

  const update = useCallback(
    async (id: string, input: Omit<AdminProduct, "id" | "created_at" | "updated_at">) => {
      await fetch(`${BASE}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (id: string) => {
      await fetch(`${BASE}/${id}`, { method: "DELETE" });
      await refresh();
    },
    [refresh],
  );

  const storeProducts = useMemo(() => adminProducts.map(adminToProduct), [adminProducts]);

  const value = useMemo(
    () => ({ adminProducts, storeProducts, loading, refresh, create, update, remove }),
    [adminProducts, storeProducts, loading, refresh, create, update, remove],
  );

  return <AdminCatalogContext.Provider value={value}>{children}</AdminCatalogContext.Provider>;
}

export function useAdminCatalog(): AdminCatalogContextValue {
  const context = useContext(AdminCatalogContext);
  if (!context) throw new Error("useAdminCatalog must be used within AdminCatalogProvider");
  return context;
}
