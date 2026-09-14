import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import { UserProfileResponse } from '../types';

export interface AuthContextType {
  user: UserProfileResponse | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<UserProfileResponse | null>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfileResponse | null>(null);
  const [token, setToken] = useState<string | null>(() => apiService.getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = useCallback(async () => {
    const currentToken = apiService.getAuthToken();
    if (!currentToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await apiService.getCurrentUser();
      if (profile) {
        setUser(profile);
        setToken(currentToken);
      } else {
        setUser(null);
        setToken(null);
      }
    } catch {
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();

    const handleAuthChange = () => {
      const currentToken = apiService.getAuthToken();
      setToken(currentToken);
      if (currentToken) {
        apiService.getCurrentUser().then((profile) => {
          setUser(profile);
        }).catch(() => {
          setUser(null);
        });
      } else {
        setUser(null);
      }
    };

    window.addEventListener('agent63_auth_change', handleAuthChange);
    return () => {
      window.removeEventListener('agent63_auth_change', handleAuthChange);
    };
  }, [refreshUser]);

  const login = async (username: string, password: string): Promise<UserProfileResponse | null> => {
    const tokenResp = await apiService.login(username, password);
    setToken(tokenResp.access_token);
    const profile = await apiService.getCurrentUser();
    setUser(profile);
    window.dispatchEvent(new Event('agent63_auth_change'));
    return profile;
  };

  const logout = async (): Promise<void> => {
    try {
      await apiService.logout();
    } finally {
      setUser(null);
      setToken(null);
      window.dispatchEvent(new Event('agent63_auth_change'));
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
