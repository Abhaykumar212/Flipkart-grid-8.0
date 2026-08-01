import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CartProvider } from "./context/CartContext";
import { TrackerProvider } from "./context/TrackerContext";
import { Layout } from "./components/layout/Layout";
import Home from "./routes/Home";
import ProductDetail from "./routes/ProductDetail";
import CartPage from "./routes/CartPage";
import CheckoutPage from "./routes/CheckoutPage";
import SearchResultsPage from "./routes/SearchResultsPage";
import PipelineConsole from "./routes/PipelineConsole";

export default function App() {
  return (
    <BrowserRouter>
      <CartProvider>
        <TrackerProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="product/:slug" element={<ProductDetail />} />
              <Route path="cart" element={<CartPage />} />
              <Route path="checkout" element={<CheckoutPage />} />
              <Route path="search" element={<SearchResultsPage />} />
              <Route path="pipeline" element={<PipelineConsole />} />
            </Route>
          </Routes>
        </TrackerProvider>
      </CartProvider>
    </BrowserRouter>
  );
}
