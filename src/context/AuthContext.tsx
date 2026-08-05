import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { eventTimeline } from "../lib/eventTimeline";

/**
 * Mock account system — email-only "sign in", no password (see
 * `backend/accounts.py`'s docstring for why). The point isn't access control,
 * it's giving a shopper's session history somewhere durable to attach to, so
 * "Real user/account history" is backed by an actual `users`/`orders` table
 * instead of just localStorage.
 */

export interface AuthUser {
  id: string;
  email: string;
  name: string;
}

const STORAGE_KEY = "fk-user-v1";

interface AuthContextValue {
  user: AuthUser | null;
  login: (email: string, name: string) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser());

  const login = useCallback(async (email: string, name: string) => {
    const response = await fetch("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.detail ?? "Sign-in failed");
    }
    const data = await response.json();
    const nextUser: AuthUser = data.user;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser));
    setUser(nextUser);

    // Roll this browser session's history into the account immediately —
    // otherwise a shopper who signs in mid-session sees an empty history
    // until their *next* visit.
    void fetch("http://localhost:8000/api/auth/link-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: eventTimeline.getSessionId(), user_id: nextUser.id }),
    }).catch(() => undefined);

    return nextUser;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({ user, login, logout }), [user, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
