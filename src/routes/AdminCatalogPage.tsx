import { useState } from "react";
import { Link } from "react-router-dom";
import { Pencil, Trash2, PlusCircle } from "lucide-react";
import { useAdminCatalog, type AdminProduct } from "../context/AdminCatalogContext";
import { formatINR } from "../lib/format";
import { Button } from "../components/ui/Button";

type FormState = Omit<AdminProduct, "id" | "created_at" | "updated_at">;

const EMPTY_FORM: FormState = {
  title: "",
  brand: "",
  category: "electronics",
  mrp: 0,
  selling_price: 0,
  image_url: "",
  stock_qty: 10,
  description: "",
};

const CATEGORIES = ["mobiles", "electronics", "audio", "appliances", "fashion"];

/**
 * Production product/catalog backend — a real admin surface over
 * `backend/main.py`'s `/api/catalog/products` CRUD (SQLite `admin_products`
 * table), not a mock. Anything created here shows up immediately in the
 * "Just Added by Sellers" home rail and in search — see AdminCatalogContext.
 */
export default function AdminCatalogPage() {
  const { adminProducts, loading, create, update, remove } = useAdminCatalog();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const startEdit = (product: AdminProduct) => {
    setEditingId(product.id);
    setForm({
      title: product.title,
      brand: product.brand,
      category: product.category,
      mrp: product.mrp,
      selling_price: product.selling_price,
      image_url: product.image_url,
      stock_qty: product.stock_qty,
      description: product.description,
    });
  };

  const resetForm = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || form.selling_price <= 0) return;
    setSubmitting(true);
    try {
      if (editingId) await update(editingId, form);
      else await create(form);
      resetForm();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="bg-white p-4 sm:p-6">
        <h1 className="text-fk-lg font-semibold text-fk-ink">Catalog Admin</h1>
        <p className="text-fk-sm text-fk-muted">
          Real backend-authored products (SQLite), merged into the storefront —{" "}
          <Link to="/" className="text-fk-blue">see them on Home</Link>.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="bg-white p-4 sm:p-6">
          <h2 className="mb-3 text-fk-md font-semibold text-fk-ink">
            Products ({adminProducts.length})
          </h2>
          {loading ? (
            <p className="text-fk-sm text-fk-muted">Loading…</p>
          ) : adminProducts.length === 0 ? (
            <p className="text-fk-sm text-fk-muted">No admin products yet — add one on the right.</p>
          ) : (
            <div className="flex flex-col divide-y divide-fk-border">
              {adminProducts.map((p) => (
                <div key={p.id} className="flex items-center gap-3 py-3">
                  <img
                    src={p.image_url || "https://rukminim2.flixcart.com/image/64/64/xif0q/cellphone/placeholder.png"}
                    alt=""
                    className="h-12 w-12 rounded object-contain"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-fk-md font-medium text-fk-ink">{p.title}</p>
                    <p className="text-fk-xs text-fk-muted">
                      {p.brand} · {p.category} · stock {p.stock_qty}
                    </p>
                  </div>
                  <p className="text-fk-md font-semibold text-fk-ink">{formatINR(p.selling_price)}</p>
                  <button onClick={() => startEdit(p)} className="p-1.5 text-fk-blue" aria-label="Edit">
                    <Pencil size={16} />
                  </button>
                  <button onClick={() => remove(p.id)} className="p-1.5 text-fk-flame" aria-label="Delete">
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="h-fit bg-white p-4 sm:p-6">
          <h2 className="mb-3 flex items-center gap-2 text-fk-md font-semibold text-fk-ink">
            <PlusCircle size={16} /> {editingId ? "Edit product" : "Add product"}
          </h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3" data-testid="admin-catalog-form">
            <input
              placeholder="Title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="rounded border border-fk-border px-3 py-2 text-fk-sm"
              required
            />
            <input
              placeholder="Brand"
              value={form.brand}
              onChange={(e) => setForm({ ...form, brand: e.target.value })}
              className="rounded border border-fk-border px-3 py-2 text-fk-sm"
            />
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="rounded border border-fk-border px-3 py-2 text-fk-sm"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                placeholder="MRP"
                value={form.mrp || ""}
                onChange={(e) => setForm({ ...form, mrp: Number(e.target.value) })}
                className="rounded border border-fk-border px-3 py-2 text-fk-sm"
              />
              <input
                type="number"
                placeholder="Selling price"
                value={form.selling_price || ""}
                onChange={(e) => setForm({ ...form, selling_price: Number(e.target.value) })}
                className="rounded border border-fk-border px-3 py-2 text-fk-sm"
                required
              />
            </div>
            <input
              type="number"
              placeholder="Stock quantity"
              value={form.stock_qty}
              onChange={(e) => setForm({ ...form, stock_qty: Number(e.target.value) })}
              className="rounded border border-fk-border px-3 py-2 text-fk-sm"
            />
            <input
              placeholder="Image URL"
              value={form.image_url}
              onChange={(e) => setForm({ ...form, image_url: e.target.value })}
              className="rounded border border-fk-border px-3 py-2 text-fk-sm"
            />
            <textarea
              placeholder="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="rounded border border-fk-border px-3 py-2 text-fk-sm"
              rows={3}
            />
            <div className="flex gap-2">
              <Button type="submit" variant="primary" disabled={submitting}>
                {submitting ? "Saving…" : editingId ? "Save changes" : "Add product"}
              </Button>
              {editingId && (
                <Button type="button" variant="outline" onClick={resetForm}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
