import { createContext, useContext, useEffect, useState } from 'react';
import ApiClient from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setTokenState] = useState(ApiClient.getToken());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      const storedToken = ApiClient.getToken();
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const userData = await ApiClient.getMe();
        setUser(userData);
      } catch (err) {
        console.error('Failed to load authenticated user:', err);
        ApiClient.setToken(null);
        setTokenState(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    loadUser();
  }, []);

  const login = async (email, password) => {
    const data = await ApiClient.login(email, password);
    setTokenState(data.access_token);
    const userData = await ApiClient.getMe();
    setUser(userData);
    return userData;
  };

  const register = async (name, email, password) => {
    const data = await ApiClient.register(name, email, password);
    return data;
  };

  const logout = () => {
    ApiClient.setToken(null);
    setTokenState(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

