"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { clearAuth, fetchCurrentUser, getAuthToken, getStoredUser, storeAuth } from "../lib/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function hydrateAuth() {
      const token = getAuthToken();
      const cachedUser = getStoredUser();
      if (!token) {
        if (isMounted) {
          setIsAuthenticated(false);
          setUser(null);
          setIsReady(true);
        }
        return;
      }

      if (cachedUser && isMounted) {
        setUser(cachedUser);
      }

      try {
        const me = await fetchCurrentUser();
        if (!me) {
          clearAuth();
          if (isMounted) {
            setIsAuthenticated(false);
            setUser(null);
          }
        } else if (isMounted) {
          storeAuth(token, me);
          setIsAuthenticated(true);
          setUser(me);
        }
      } catch {
        clearAuth();
        if (isMounted) {
          setIsAuthenticated(false);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsReady(true);
        }
      }
    }

    hydrateAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const value = useMemo(
    () => ({
      isAuthenticated,
      user,
      isReady,
      login(nextUser, token) {
        storeAuth(token, nextUser);
        setUser(nextUser || null);
        setIsAuthenticated(true);
      },
      logout() {
        clearAuth();
        setIsAuthenticated(false);
        setUser(null);
      },
    }),
    [isAuthenticated, isReady, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
