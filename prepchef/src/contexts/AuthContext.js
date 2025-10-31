import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../services/api';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');

    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const login = async (credentials) => {
    const response = await api.login(credentials);
    const { access_token: accessToken, user: userPayload } = response;

    const userData = userPayload || { email: credentials.email };

    setToken(accessToken);
    setUser(userData);

    localStorage.setItem('token', accessToken);
    localStorage.setItem('user', JSON.stringify(userData));

    return response;
  };

  const register = async (userData) => {
    const response = await api.register(userData);
    const { access_token: accessToken, user: userPayload } = response;

    const storedUser =
      userPayload || { email: userData.email, name: userData.name };

    setToken(accessToken);
    setUser(storedUser);

    localStorage.setItem('token', accessToken);
    localStorage.setItem('user', JSON.stringify(storedUser));

    return response;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const value = {
    user,
    token,
    login,
    register,
    logout,
    isAuthenticated: Boolean(token),
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
