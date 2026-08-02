import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";

const STORAGE_KEY = "fk-cart-v1";

export interface CartItem {
  productId: string;
  quantity: number;
  /** Human-readable option selected on the PDP, e.g. "Size: M". */
  variant?: string;
  /**
   * ISO timestamp of the first add. Not used by the cart UI, but it's the field
   * `ProductSignals.addedToCartAt` / `cartDwellMs` will be derived from once the
   * abandonment agent lands — capturing it now avoids a migration.
   */
  addedAt: string;
}

export interface CartState {
  items: CartItem[];
  promoCode: string | null;
}

// `addedAt` is overridden only by demo scenarios so dwell-time signals can
// represent a realistic session while normal cart additions use the clock.
export type CartAction =
  | { type: "ADD_ITEM"; productId: string; quantity?: number; variant?: string; addedAt?: string }
  | { type: "REMOVE_ITEM"; productId: string; variant?: string }
  | { type: "UPDATE_QUANTITY"; productId: string; quantity: number; variant?: string }
  | { type: "APPLY_PROMO"; code: string }
  | { type: "REMOVE_PROMO" }
  | { type: "CLEAR_CART" };

const EMPTY_STATE: CartState = { items: [], promoCode: null };

export function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "ADD_ITEM": {
      const quantity = action.quantity ?? 1;
      const existing = state.items.find(
        (item) => item.productId === action.productId && item.variant === action.variant,
      );

      // Increment the existing line rather than pushing a duplicate row, and
      // keep the original `addedAt` so dwell time measures from the first add.
      if (existing) {
        return {
          ...state,
          items: state.items.map((i) =>
            i.productId === action.productId && i.variant === action.variant
              ? { ...i, quantity: i.quantity + quantity }
              : i,
          ),
        };
      }

      return {
        ...state,
        items: [
          ...state.items,
          {
            productId: action.productId,
            quantity,
            variant: action.variant,
            addedAt: action.addedAt ?? new Date().toISOString(),
          },
        ],
      };
    }

    case "REMOVE_ITEM":
      return {
        ...state,
        items: state.items.filter(
          (item) => !(item.productId === action.productId && item.variant === action.variant),
        ),
      };

    case "UPDATE_QUANTITY": {
      // Clamped at 1 — dropping to zero never silently removes a line, removal
      // is always an explicit REMOVE_ITEM.
      const quantity = Math.max(1, action.quantity);
      return {
        ...state,
        items: state.items.map((i) =>
          i.productId === action.productId && i.variant === action.variant
            ? { ...i, quantity }
            : i,
        ),
      };
    }

    case "APPLY_PROMO":
      return { ...state, promoCode: action.code };

    case "REMOVE_PROMO":
      return { ...state, promoCode: null };

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
    const promoCode = typeof (parsed as CartState).promoCode === "string"
      ? (parsed as CartState).promoCode
      : null;
    return { items, promoCode };
  } catch {
    return EMPTY_STATE;
  }
}

interface CartContextValue {
  items: CartItem[];
  promoCode: string | null;
  /** Total quantity across all lines — what the navbar badge shows. */
  count: number;
  addItem: (productId: string, quantity?: number, variant?: string, addedAt?: string) => void;
  removeItem: (productId: string, variant?: string) => void;
  updateQuantity: (productId: string, quantity: number, variant?: string) => void;
  applyPromo: (code: string) => void;
  removePromo: () => void;
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
      promoCode: state.promoCode,
      count: state.items.reduce((sum, i) => sum + i.quantity, 0),
      addItem: (productId, quantity, variant, addedAt) =>
        dispatch({ type: "ADD_ITEM", productId, quantity, variant, addedAt }),
      removeItem: (productId, variant) =>
        dispatch({ type: "REMOVE_ITEM", productId, variant }),
      updateQuantity: (productId, quantity, variant) =>
        dispatch({ type: "UPDATE_QUANTITY", productId, quantity, variant }),
      applyPromo: (code) => dispatch({ type: "APPLY_PROMO", code }),
      removePromo: () => dispatch({ type: "REMOVE_PROMO" }),
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
