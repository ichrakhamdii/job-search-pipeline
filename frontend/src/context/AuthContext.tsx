import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import * as api from "../services/api";

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!api.getAccessToken());

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.login(email, password);
    api.storeTokens(tokens);
    setIsAuthenticated(true);
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const tokens = await api.signup(email, password);
    api.storeTokens(tokens);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    api.clearTokens();
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
