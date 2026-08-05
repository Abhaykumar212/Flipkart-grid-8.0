import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, LogIn } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export function SignInModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) {
      setError("Enter a valid email address");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await login(email.trim(), name.trim());
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            className="relative w-full max-w-sm rounded-md bg-white p-6 shadow-2xl"
          >
            <button onClick={onClose} className="absolute right-4 top-4 text-fk-muted hover:text-fk-ink">
              <X size={18} />
            </button>
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-50 text-fk-blue">
                <LogIn size={18} />
              </div>
              <div>
                <h2 className="text-fk-lg font-semibold text-fk-ink">Sign in</h2>
                <p className="text-fk-xs text-fk-muted">Demo account — email only, no password</p>
              </div>
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="rounded border border-fk-border px-3 py-2 text-fk-md outline-none focus:border-fk-blue"
                data-testid="signin-email"
                autoFocus
              />
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Name (optional)"
                className="rounded border border-fk-border px-3 py-2 text-fk-md outline-none focus:border-fk-blue"
              />
              {error && <p className="text-fk-xs text-fk-flame">{error}</p>}
              <button
                type="submit"
                disabled={submitting}
                data-testid="signin-submit"
                className="rounded bg-fk-blue px-4 py-2.5 text-fk-md font-semibold text-white disabled:opacity-60"
              >
                {submitting ? "Signing in…" : "Sign in"}
              </button>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
