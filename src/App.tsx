import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CartProvider } from "./context/CartContext";
import { WishlistProvider } from "./context/WishlistContext";
import { TrackerProvider } from "./context/TrackerContext";
import { EventTimelineProvider } from "./context/EventTimelineContext";
import { InterventionProvider } from "./context/InterventionContext";
import { AuthProvider } from "./context/AuthContext";
import { LanguageProvider } from "./context/LanguageContext";
import { AdminCatalogProvider } from "./context/AdminCatalogContext";
import { Layout } from "./components/layout/Layout";
import Home from "./routes/Home";
import ProductDetail from "./routes/ProductDetail";
import CartPage from "./routes/CartPage";
import CheckoutPage from "./routes/CheckoutPage";
import SearchResultsPage from "./routes/SearchResultsPage";
import PipelineConsole from "./routes/PipelineConsole";
import InterventionLab from "./routes/InterventionLab";
import ReEngagementDashboard from "./routes/ReEngagementDashboard";
import AccountPage from "./routes/AccountPage";
import AdminCatalogPage from "./routes/AdminCatalogPage";
import ABTestingDashboard from "./routes/ABTestingDashboard";
import SmartSearchPage from "./routes/SmartSearchPage";
import { EmailCaptureModal } from "./components/ui/EmailCaptureModal";

export default function App() {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <AuthProvider>
          <AdminCatalogProvider>
            <CartProvider>
              <WishlistProvider>
                <EventTimelineProvider>
                  <TrackerProvider>
                    <InterventionProvider>
                      <Routes>
                        <Route element={<Layout />}>
                          <Route index element={<Home />} />
                          <Route path="product/:slug" element={<ProductDetail />} />
                          <Route path="cart" element={<CartPage />} />
                          <Route path="checkout" element={<CheckoutPage />} />
                          <Route path="search" element={<SearchResultsPage />} />
                          <Route path="pipeline" element={<PipelineConsole />} />
                          <Route path="intervention-lab" element={<InterventionLab />} />
                          <Route path="reengagement" element={<ReEngagementDashboard />} />
                          <Route path="account" element={<AccountPage />} />
                          <Route path="admin/catalog" element={<AdminCatalogPage />} />
                          <Route path="ab-testing" element={<ABTestingDashboard />} />
                          <Route path="smart-search" element={<SmartSearchPage />} />
                        </Route>
                      </Routes>
                      <EmailCaptureModal />
                    </InterventionProvider>
                  </TrackerProvider>
                </EventTimelineProvider>
              </WishlistProvider>
            </CartProvider>
          </AdminCatalogProvider>
        </AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  );
}
