import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import { sendCartAdd } from "../lib/tracker";

const STORAGE_KEY = "fk-cart-v1";

export interface CartItem {
  productId: string;
  quantity: number;
  /**
   * ISO timestamp of the first add. Not used by the cart UI, but it's the field
   * `ProductSignals.addedToCartAt` / `cartDwellMs` will be derived from once the
   * abandonment agent lands — capturing it now avoids a migration.
   */
  addedAt: string;
}

export interface CartState {
  items: CartItem[];
}

export type CartAction =
  // `addedAt` is an override used only by the demo scenario loader, which
  // backdates the cart so dwell-time features look like a real session
  // instead of one that started milliseconds ago.
  | { type: "ADD_ITEM"; productId: string; quantity?: number; addedAt?: string }
  | { type: "REMOVE_ITEM"; productId: string }
  | { type: "UPDATE_QUANTITY"; productId: string; quantity: number }
  | { type: "CLEAR_CART" };

const EMPTY_STATE: CartState = { items: [] };

export function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "ADD_ITEM": {
      const quantity = action.quantity ?? 1;
      const existing = state.items.find((i) => i.productId === action.productId);

      // Increment the existing line rather than pushing a duplicate row, and
      // keep the original `addedAt` so dwell time measures from the first add.
      if (existing) {
        return {
          items: state.items.map((i) =>
            i.productId === action.productId
              ? { ...i, quantity: i.quantity + quantity }
              : i,
          ),
        };
      }

      return {
        items: [
          ...state.items,
          {
            productId: action.productId,
            quantity,
            addedAt: action.addedAt ?? new Date().toISOString(),
          },
        ],
      };
    }

    case "REMOVE_ITEM":
      return { items: state.items.filter((i) => i.productId !== action.productId) };

    case "UPDATE_QUANTITY": {
      // Clamped at 1 — dropping to zero never silently removes a line, removal
      // is always an explicit REMOVE_ITEM.
      const quantity = Math.max(1, action.quantity);
      return {
        items: state.items.map((i) =>
          i.productId === action.productId ? { ...i, quantity } : i,
        ),
      };
    }

    case "CLEAR_CART":
      return EMPTY_STATE;

    default:
      return state;
  }
}

/** Reads persisted cart state, falling back to empty on missing/corrupt/blocked storage. */
function readStoredCart(): CartState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_STATE;

    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !Array.isArray((parsed as CartState).items)
    ) {
      return EMPTY_STATE;
    }

    const items = (parsed as CartState).items.filter(
      (i): i is CartItem =>
        typeof i?.productId === "string" &&
        typeof i?.quantity === "number" &&
        i.quantity > 0,
    );
    return { items };
  } catch {
    return EMPTY_STATE;
  }
}

interface CartContextValue {
  items: CartItem[];
  /** Total quantity across all lines — what the navbar badge shows. */
  count: number;
  addItem: (productId: string, quantity?: number, addedAt?: string) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
}

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, undefined, readStoredCart);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Storage full or unavailable (private mode) — the in-memory cart still works.
    }
  }, [state]);

  const value = useMemo<CartContextValue>(
    () => ({
      items: state.items,
      count: state.items.reduce((sum, i) => sum + i.quantity, 0),
      addItem: (productId, quantity, addedAt) => {
        dispatch({ type: "ADD_ITEM", productId, quantity, addedAt });
        // Fire-and-forget, outside the reducer so that stays pure. Releases the
        // inventory hold the pipeline may have placed on this product.
        void sendCartAdd(productId);
      },
      removeItem: (productId) => dispatch({ type: "REMOVE_ITEM", productId }),
      updateQuantity: (productId, quantity) =>
        dispatch({ type: "UPDATE_QUANTITY", productId, quantity }),
      clearCart: () => dispatch({ type: "CLEAR_CART" }),
    }),
    [state],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}
