import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Package, Clock, User as UserIcon } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { formatINR } from "../lib/format";

interface OrderRecord {
  id: string;
  session_id: string;
  items: { product_id: string; title: string; quantity: number; selling_price: number }[];
  total_inr: number;
  status: string;
  created_at: number;
}

interface SessionRecord {
  session_id: string;
  started_at: number;
  last_seen_at: number;
  interventions_shown: number;
  held: number;
}

/**
 * Real user/account history — reads `GET /api/users/{id}/history`
 * (backend/accounts.py), which rolls up every order placed and every browser
 * session linked to this account. Not derived from localStorage: a fresh
 * browser signed into the same email sees the same history.
 */
export default function AccountPage() {
  const { user } = useAuth();
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    fetch(`http://localhost:8000/api/users/${user.id}/history`)
      .then((r) => r.json())
      .then((data) => {
        setOrders(data.orders ?? []);
        setSessions(data.sessions ?? []);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) return <Navigate to="/" replace />;

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="flex items-center gap-3 bg-white p-4 sm:p-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-fk-blue">
          <UserIcon size={22} />
        </div>
        <div>
          <h1 className="text-fk-lg font-semibold text-fk-ink">{user.name || "Shopper"}</h1>
          <p className="text-fk-sm text-fk-muted">{user.email}</p>
        </div>
      </div>

      <div className="bg-white p-4 sm:p-6">
        <h2 className="mb-3 flex items-center gap-2 text-fk-md font-semibold text-fk-ink">
          <Package size={16} /> Order history ({orders.length})
        </h2>
        {loading ? (
          <p className="text-fk-sm text-fk-muted">Loading…</p>
        ) : orders.length === 0 ? (
          <p className="text-fk-sm text-fk-muted">
            No orders yet. Anything you buy through <Link to="/cart" className="text-fk-blue">checkout</Link> will show up here.
          </p>
        ) : (
          <div className="flex flex-col divide-y divide-fk-border">
            {orders.map((order) => (
              <div key={order.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-fk-md font-medium text-fk-ink">{order.id}</p>
                  <p className="text-fk-xs text-fk-muted">
                    {order.items.length} item(s) · {new Date(order.created_at * 1000).toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-fk-md font-semibold text-fk-ink">{formatINR(order.total_inr)}</p>
                  <p className="text-fk-xs capitalize text-green-700">{order.status}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-white p-4 sm:p-6">
        <h2 className="mb-3 flex items-center gap-2 text-fk-md font-semibold text-fk-ink">
          <Clock size={16} /> Session history ({sessions.length})
        </h2>
        {sessions.length === 0 ? (
          <p className="text-fk-sm text-fk-muted">No linked sessions yet.</p>
        ) : (
          <div className="flex flex-col divide-y divide-fk-border">
            {sessions.map((s) => (
              <div key={s.session_id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-mono text-fk-xs text-fk-muted">{s.session_id}</p>
                  <p className="text-fk-xs text-fk-muted">
                    {new Date(s.started_at * 1000).toLocaleString()}
                  </p>
                </div>
                <p className="text-fk-xs text-fk-muted">
                  {s.interventions_shown} intervention(s) shown · {s.held} held
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
