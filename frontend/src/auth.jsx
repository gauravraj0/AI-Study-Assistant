import { createContext, useContext, useEffect, useState } from "react";
import { api, clearSession, getStoredUser, getToken, setSession } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser());
  const [loading, setLoading] = useState(!!getToken());

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api("/auth/me")
      .then((u) => setUser(u))
      .catch(() => {
        // Ignore if the user logged in with a different token while this
        // request was in flight.
        if (getToken() === token) {
          clearSession();
          setUser(null);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const r = await api("/auth/login", { method: "POST", body: { email, password } });
    setSession(r.access_token, r.user);
    setUser(r.user);
  };

  const register = async (name, email, password) => {
    const r = await api("/auth/register", { method: "POST", body: { name, email, password } });
    setSession(r.access_token, r.user);
    setUser(r.user);
  };

  const logout = () => {
    clearSession();
    setUser(null);
  };

  return <AuthCtx.Provider value={{ user, loading, login, register, logout }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
