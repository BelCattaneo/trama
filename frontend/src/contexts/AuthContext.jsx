import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
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
    refresh();
  }, [initialUser, refresh]);

  const logout = useCallback(async () => {
    try {
      await apiPost("/api/auth/logout");
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, logout, refresh }),
    [user, loading, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
