import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api, clearToken, getRefreshToken, getToken, setRefreshToken, setToken } from '../api/client.js';

const AppContext = createContext(null);
const LANGUAGE_KEY = 'matchflow_language';

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [globalError, setGlobalError] = useState('');
  const [loading, setLoading] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [language, setLanguageState] = useState(() => localStorage.getItem(LANGUAGE_KEY) || 'pt');

  function setLanguage(lang) {
    setLanguageState(lang);
    localStorage.setItem(LANGUAGE_KEY, lang);
  }

  function persistSession(res) {
    setToken(res.access_token);
    if (res.refresh_token) setRefreshToken(res.refresh_token);
    setUser(res.user);
  }

  async function login(email, password, rememberSession = false) {
    setLoading(true); setGlobalError('');
    try {
      const res = await api.login(email, password, rememberSession);
      persistSession(res);
      return true;
    } catch (e) { setGlobalError(e.message); return false; }
    finally { setLoading(false); }
  }

  async function register(payload) {
    setLoading(true); setGlobalError('');
    try {
      await api.register(payload);
      const ok = await login(payload.email, payload.password, true);
      return ok;
    } catch (e) { setGlobalError(e.message); return false; }
    finally { setLoading(false); }
  }

  async function forgotPassword(email) {
    setLoading(true); setGlobalError('');
    try { return await api.forgotPassword(email); }
    catch (e) { setGlobalError(e.message); return null; }
    finally { setLoading(false); }
  }

  async function resetPassword(token, newPassword) {
    setLoading(true); setGlobalError('');
    try { await api.resetPassword(token, newPassword); return true; }
    catch (e) { setGlobalError(e.message); return false; }
    finally { setLoading(false); }
  }

  async function logout() {
    const refreshToken = getRefreshToken();
    try { if (refreshToken) await api.logout(refreshToken); } catch { /* best effort */ }
    clearToken(); setUser(null);
  }

  useEffect(() => {
    async function restoreSession() {
      try {
        if (getToken()) {
          const r = await api.me();
          setUser(r.user);
          return;
        }
        const refreshToken = getRefreshToken();
        if (refreshToken) {
          const refreshed = await api.refresh(refreshToken);
          persistSession(refreshed);
        }
      } catch {
        clearToken(); setUser(null);
      } finally {
        setAuthReady(true);
      }
    }
    restoreSession();
  }, []);

  const value = useMemo(() => ({
    user, login, register, forgotPassword, resetPassword, logout, loading, authReady,
    setLoading, globalError, setGlobalError, language, setLanguage,
  }), [user, loading, authReady, globalError, language]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() { return useContext(AppContext); }
