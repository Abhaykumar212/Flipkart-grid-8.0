import { Heart } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ProductCard } from "../components/home/ProductCard";
import { Button } from "../components/ui/Button";
import { useWishlist } from "../context/WishlistContext";
import { productById } from "../data/products";

export default function WishlistPage() {
  const navigate = useNavigate();
  const { productIds } = useWishlist();
  const wishlistedProducts = productIds.flatMap((id) => {
    const product = productById.get(id);
    return product ? [product] : [];
  });

  if (wishlistedProducts.length === 0) {
    return (
      <section className="flex min-h-[480px] flex-col items-center justify-center bg-white px-6 py-16 text-center" data-testid="wishlist-empty">
        <Heart className="h-16 w-16 text-fk-border" strokeWidth={1.5} />
        <h1 className="mt-4 text-fk-xl font-medium text-fk-ink">Your wishlist is empty</h1>
        <p className="mt-2 text-fk-base text-fk-muted">Save products you like and find them here anytime.</p>
        <Button className="mt-5" onClick={() => navigate("/products")}>Explore products</Button>
      </section>
    );
  }

  return (
    <section className="bg-white shadow-fk-card">
      <header className="border-b border-fk-border px-4 py-5 sm:px-6">
        <h1 className="text-xl font-medium text-fk-ink">My Wishlist ({wishlistedProducts.length})</h1>
        <p className="mt-1 text-fk-base text-fk-muted">Your saved products are stored on this device.</p>
      </header>
      <div className="grid grid-cols-2 gap-px bg-fk-border p-px sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {wishlistedProducts.map((product) => (
          <ProductCard key={product.id} product={product} fixedWidth={false} />
        ))}
      </div>
    </section>
  );
}
