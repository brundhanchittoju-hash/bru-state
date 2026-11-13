import React, { createContext, useContext, useEffect, useState } from "react";
import { api, clearTokens, getAccessToken, setTokens } from "@/lib/api";
import { RoleCode, TokenResponse, User } from "@/types";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  logout: () => void;
  hasRole: (roles: RoleCode[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const cached = localStorage.getItem("user_data");
    return cached ? JSON.parse(cached) : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(() => {
    // Only show full loading spinner if token exists but user data isn't loaded yet
    const token = getAccessToken();
    const cached = localStorage.getItem("user_data");
    return !!token && !cached;
  });

  const fetchProfile = async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await api.get<User>("/auth/me");
      setUser(profile);
      localStorage.setItem("user_data", JSON.stringify(profile));
    } catch (err: any) {
      if (err?.status === 401) {
        setUser(null);
        clearTokens();
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();

    const handleLogoutEvent = () => {
      logout();
    };
    window.addEventListener("auth:logout", handleLogoutEvent);
    return () => window.removeEventListener("auth:logout", handleLogoutEvent);
  }, []);

  const login = async (credentials: { email: string; password: string }) => {
    setIsLoading(true);
    try {
      const data = await api.post<TokenResponse>("/auth/login", credentials);
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      localStorage.setItem("user_data", JSON.stringify(data.user));
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.post("/auth/logout").catch(() => {});
    clearTokens();
    setUser(null);
  };

  const hasRole = (roles: RoleCode[]): boolean => {
    if (!user || !user.role) return false;
    return roles.includes(user.role.code);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
