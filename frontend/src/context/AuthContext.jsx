import { createContext, useContext, useEffect, useMemo, useState } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

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
        sessionStorage.removeItem("campus.access");
        sessionStorage.removeItem("campus.refresh");
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
        sessionStorage.removeItem("campus.access");
        sessionStorage.removeItem("campus.refresh");
        setUser(null);
        throw error;
      }
    },
    logout() {
      sessionStorage.removeItem("campus.access");
      sessionStorage.removeItem("campus.refresh");
      setUser(null);
    },
  }), [user, checking]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
