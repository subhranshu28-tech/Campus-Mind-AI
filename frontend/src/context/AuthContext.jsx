import { createContext, useContext, useEffect, useMemo, useState } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

function clearStoredSession() {
  sessionStorage.removeItem("campus.access");
  sessionStorage.removeItem("campus.refresh");
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      if (!sessionStorage.getItem("campus.access")) {
        setChecking(false);
        return;
      }
      try {
        const { data } = await api.get("/auth/me/");
        setUser(data);
      } catch {
        clearStoredSession();
      } finally {
        setChecking(false);
      }
    };
    loadUser();
    const expire = () => setUser(null);
    window.addEventListener("campus:session-expired", expire);
    return () => window.removeEventListener("campus:session-expired", expire);
  }, []);

  const value = useMemo(() => ({
    user,
    checking,
    async login(username, password) {
      const { data } = await api.post("/auth/token/", { username, password });
      sessionStorage.setItem("campus.access", data.access);
      sessionStorage.setItem("campus.refresh", data.refresh);
      try {
        const profile = await api.get("/auth/me/");
        setUser(profile.data);
      } catch (error) {
        clearStoredSession();
        setUser(null);
        throw error;
      }
    },
    async logout() {
      const refresh = sessionStorage.getItem("campus.refresh");
      const access = sessionStorage.getItem("campus.access");
      clearStoredSession();
      setUser(null);
      if (!refresh) return;
      try {
        // Revoke the refresh token server-side as well as clearing the tab.
        await api.post("/auth/logout/", { refresh }, {
          headers: access ? { Authorization: `Bearer ${access}` } : undefined,
        });
      } catch {
        // Logout must always succeed locally even if the network is down.
      }
    },
  }), [user, checking]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
