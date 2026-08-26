import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import api from "../api/client";
import { clearStoredToken, getStoredToken, setStoredToken } from "../auth/token";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  applyToken: (accessToken: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    api
      .get<User>("/api/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => {
        clearStoredToken();
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  const login = async (email: string, password: string) => {
    const { data } = await api.post<{ access_token: string }>("/api/auth/login", {
      email,
      password,
    });
    setStoredToken(data.access_token);
    setToken(data.access_token);
  };

  const applyToken = (accessToken: string) => {
    setStoredToken(accessToken);
    setToken(accessToken);
  };

  const logout = () => {
    clearStoredToken();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, applyToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
