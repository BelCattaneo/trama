import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiGet, apiPost } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children, initialUser = undefined }) {
  const [user, setUser] = useState(initialUser);
  const [loading, setLoading] = useState(initialUser === undefined);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiGet("/api/me");
      if (response.ok) {
        setUser(await response.json());
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialUser !== undefined) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const response = await apiGet("/api/me");
        if (cancelled) return;
        if (response.ok) {
          setUser(await response.json());
        } else {
          setUser(null);
        }
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialUser]);

  async function logout() {
    try {
      await apiPost("/api/auth/logout");
    } finally {
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
