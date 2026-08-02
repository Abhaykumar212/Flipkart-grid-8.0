import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";

const STORAGE_KEY = "fk-wishlist-v1";

export interface WishlistState {
  productIds: string[];
}

export type WishlistAction =
  | { type: "ADD"; productId: string }
  | { type: "REMOVE"; productId: string }
  | { type: "TOGGLE"; productId: string };

const EMPTY_STATE: WishlistState = { productIds: [] };

export function wishlistReducer(state: WishlistState, action: WishlistAction): WishlistState {
  switch (action.type) {
    case "ADD":
      return state.productIds.includes(action.productId)
        ? state
        : { productIds: [...state.productIds, action.productId] };

    case "REMOVE":
      return { productIds: state.productIds.filter((id) => id !== action.productId) };

    case "TOGGLE":
      return state.productIds.includes(action.productId)
        ? { productIds: state.productIds.filter((id) => id !== action.productId) }
        : { productIds: [...state.productIds, action.productId] };

    default:
      return state;
  }
}

function readStoredWishlist(): WishlistState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_STATE;

    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !Array.isArray((parsed as WishlistState).productIds)
    ) {
      return EMPTY_STATE;
    }

    return {
      productIds: (parsed as WishlistState).productIds.filter(
        (id): id is string => typeof id === "string",
      ),
    };
  } catch {
    return EMPTY_STATE;
  }
}

interface WishlistContextValue {
  productIds: string[];
  has: (productId: string) => boolean;
  toggle: (productId: string) => void;
  add: (productId: string) => void;
  remove: (productId: string) => void;
}

const WishlistContext = createContext<WishlistContextValue | null>(null);

export function WishlistProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(wishlistReducer, undefined, readStoredWishlist);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Storage full or unavailable (private mode) — the in-memory wishlist still works.
    }
  }, [state]);

  const value = useMemo<WishlistContextValue>(
    () => ({
      productIds: state.productIds,
      has: (productId) => state.productIds.includes(productId),
      toggle: (productId) => dispatch({ type: "TOGGLE", productId }),
      add: (productId) => dispatch({ type: "ADD", productId }),
      remove: (productId) => dispatch({ type: "REMOVE", productId }),
    }),
    [state],
  );

  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>;
}

export function useWishlist(): WishlistContextValue {
  const ctx = useContext(WishlistContext);
  if (!ctx) throw new Error("useWishlist must be used within a WishlistProvider");
  return ctx;
}
