import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { CartProvider } from "./context/CartContext";
import { WishlistProvider } from "./context/WishlistContext";
import { TrackerProvider } from "./context/TrackerContext";
import { SessionProvider } from "./context/SessionContext";
import { InterventionProvider } from "./context/InterventionContext";
import { Layout } from "./components/layout/Layout";
import Home from "./routes/Home";
import ProductDetail from "./routes/ProductDetail";
import CartPage from "./routes/CartPage";
import CheckoutPage from "./routes/CheckoutPage";
import CatalogPage from "./routes/CatalogPage";
import WishlistPage from "./routes/WishlistPage";
import NotFoundPage from "./routes/NotFoundPage";
import SearchResultsPage from "./routes/SearchResultsPage";
import PipelineConsole from "./routes/PipelineConsole";
import DashboardLayout from "./routes/dashboard/DashboardLayout";
import CommandCenter from "./routes/dashboard/CommandCenter";
import DecisionTrace from "./routes/dashboard/DecisionTrace";
import SessionReplay from "./routes/dashboard/SessionReplay";
import ModelMetrics from "./routes/dashboard/ModelMetrics";
import Experiments from "./routes/dashboard/Experiments";
import ScenarioTheatre from "./routes/dashboard/ScenarioTheatre";
import Architecture from "./routes/dashboard/Architecture";
import ProofLab from "./routes/dashboard/ProofLab";
import RuntimeProof from "./routes/dashboard/RuntimeProof";

function StorefrontRoutes() {
  return (
    <SessionProvider>
      <CartProvider>
        <WishlistProvider>
          <TrackerProvider>
            <InterventionProvider>
              <Routes>
                <Route element={<Layout />}>
                  <Route index element={<Home />} />
                  <Route path="products" element={<CatalogPage />} />
                  <Route path="category/:category" element={<CatalogPage />} />
                  <Route path="product/:slug" element={<ProductDetail />} />
                  <Route path="wishlist" element={<WishlistPage />} />
                  <Route path="cart" element={<CartPage />} />
                  <Route path="checkout" element={<CheckoutPage />} />
                  <Route path="search" element={<SearchResultsPage />} />
                  <Route path="pipeline" element={<PipelineConsole />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Routes>
            </InterventionProvider>
          </TrackerProvider>
        </WishlistProvider>
      </CartProvider>
    </SessionProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="dashboard" element={<DashboardLayout />}>
          <Route index element={<CommandCenter />} />
          <Route path="sessions/:sessionId" element={<CommandCenter />} />
          <Route path="sessions/:sessionId/replay" element={<SessionReplay />} />
          <Route path="decisions/:decisionId" element={<DecisionTrace />} />
          <Route path="proof" element={<ProofLab />}>
            <Route index element={<Navigate to="scenarios" replace />} />
            <Route path="scenarios" element={<ScenarioTheatre embedded />} />
            <Route path="experiment" element={<Experiments embedded />} />
            <Route path="models" element={<ModelMetrics embedded />} />
            <Route path="runtime" element={<RuntimeProof />} />
          </Route>
          <Route path="scenarios" element={<Navigate to="/dashboard/proof/scenarios" replace />} />
          <Route path="metrics" element={<Navigate to="/dashboard/proof/models" replace />} />
          <Route path="experiments" element={<Navigate to="/dashboard/proof/experiment" replace />} />
          <Route path="architecture" element={<Architecture />} />
        </Route>
        <Route path="*" element={<StorefrontRoutes />} />
      </Routes>
    </BrowserRouter>
  );
}
