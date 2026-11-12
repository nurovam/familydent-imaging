import { StrictMode, useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ApiError, api, errorText, type Account } from './api';
import { Login } from './Login';
import { Workspace } from './Workspace';
import { DemoApp } from './main';

function Application() {
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const sessionEnd = useCallback(() => setAccount(null), []);
  const refresh = useCallback(async () => {
    setLoading(true); setError('');
    try { setAccount(await api<Account>('/auth/me')); }
    catch (e) { setAccount(null); if (!(e instanceof ApiError && e.status === 401)) setError(errorText(e)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  if (loading) return <main className="patient-page"><p role="status">Проверка сессии…</p></main>;
  if (error) return <main className="patient-page"><p className="error" role="alert">{error}</p><button className="btn" onClick={() => void refresh()}>Повторить</button></main>;
  return account ? <Workspace account={account} onSessionEnd={sessionEnd} /> : <Login onLogin={() => void refresh()} />;
}
createRoot(document.getElementById('root')!).render(<StrictMode>{location.pathname === '/demo' ? <DemoApp /> : <Application />}</StrictMode>);
