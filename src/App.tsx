import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CartProvider } from "./context/CartContext";
import { WishlistProvider } from "./context/WishlistContext";
import { TrackerProvider } from "./context/TrackerContext";
import { Layout } from "./components/layout/Layout";
import Home from "./routes/Home";
import ProductDetail from "./routes/ProductDetail";
import CartPage from "./routes/CartPage";
import CheckoutPage from "./routes/CheckoutPage";
import CatalogPage from "./routes/CatalogPage";
import WishlistPage from "./routes/WishlistPage";
import NotFoundPage from "./routes/NotFoundPage";

export default function App() {
  return (
    <BrowserRouter>
      <CartProvider>
        <WishlistProvider>
          <TrackerProvider>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="products" element={<CatalogPage />} />
                <Route path="category/:category" element={<CatalogPage />} />
                <Route path="product/:slug" element={<ProductDetail />} />
                <Route path="wishlist" element={<WishlistPage />} />
                <Route path="cart" element={<CartPage />} />
                <Route path="checkout" element={<CheckoutPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </TrackerProvider>
        </WishlistProvider>
      </CartProvider>
    </BrowserRouter>
  );
}
