import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, getAuthToken, setAuthToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(getAuthToken());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleAuthExpired = () => {
      setToken(null);
      setUser(null);
    };

    window.addEventListener('cig_auth_expired', handleAuthExpired);

    const checkAuth = async () => {
      const savedToken = getAuthToken();
      if (savedToken) {
        try {
          const profile = await api.getMe();
          setToken(savedToken);
          setUser({ username: profile.username || 'admin', role: profile.role?.name || 'ADMIN' });
        } catch {
          setAuthToken(null);
          setToken(null);
          setUser(null);
        }
      } else {
        setToken(null);
        setUser(null);
      }
      setLoading(false);
    };

    checkAuth();

    return () => {
      window.removeEventListener('cig_auth_expired', handleAuthExpired);
    };
  }, []);

  const login = async (username, password) => {
    const res = await api.login(username, password);
    setToken(res.access_token);
    setUser({ username: res.username || username, role: 'ADMIN' });
    return res;
  };

  const logout = () => {
    api.logout();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
