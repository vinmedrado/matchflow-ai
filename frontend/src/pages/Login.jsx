import { useState } from 'react';
import { useApp } from '../store/AppContext.jsx';
import { useI18n } from '../i18n.js';
import LanguageSelector from '../components/LanguageSelector.jsx';
import logo from '../assets/brand/matchflow-ai-logo.jpeg';

export default function Login({ setPage }) {
  const { login, register, forgotPassword, resetPassword, loading, globalError } = useApp();
  const { t } = useI18n();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('admin@matchflow.local');
  const [password, setPassword] = useState('admin123');
  const [name, setName] = useState('');
  const [tenantName, setTenantName] = useState('');
  const [remember, setRemember] = useState(true);
  const [devToken, setDevToken] = useState('');
  const [message, setMessage] = useState('');

  async function submit() {
    setMessage(''); setDevToken('');
    if (mode === 'login') return login(email, password, remember);
    if (mode === 'register') return register({ email, password, name: name || email, tenant_name: tenantName || undefined });
    if (mode === 'forgot') {
      const res = await forgotPassword(email);
      if (res?.dev_reset_token) setDevToken(res.dev_reset_token);
      setMessage(res?.message || 'Verifique as instruções de reset.');
      return true;
    }
    if (mode === 'reset') {
      const ok = await resetPassword(devToken, password);
      if (ok) { setMessage('Senha atualizada. Faça login novamente.'); setMode('login'); }
      return ok;
    }
  }

  function handleKey(e) { if (e.key === 'Enter') submit(); }

  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="login-copy">
          <button type="button" className="brand-pill brand-pill-button" onClick={() => setPage && setPage('Landing')}>← MatchFlow AI</button>
          <h1>{t('premiumTitle')}</h1>
          <p>{t('premiumSubtitle')}</p>
          <div className="login-benefits">
            <span>Auth SaaS</span><span>Tenant</span><span>Roles</span><span>Paper mode</span>
          </div>
        </div>
        <div className="login-card">
          <div className="login-card-top">
            <img className="login-logo-mark" src={logo} alt="MatchFlow AI" />
            <LanguageSelector compact />
          </div>
          <h2>Match<span>Flow AI</span></h2>
          <p className="text-muted">
            {mode === 'login' && 'Acesse sua organização com sessão segura.'}
            {mode === 'register' && 'Crie sua conta e tenant isolado.'}
            {mode === 'forgot' && 'Receba um token de reset. Em demo, ele aparece abaixo.'}
            {mode === 'reset' && 'Informe o token e a nova senha.'}
          </p>

          {mode === 'register' && <><label className="input-label">Nome</label><input className="input" value={name} onChange={e => setName(e.target.value)} onKeyDown={handleKey} /></>}
          <label className="input-label">{t('email')}</label>
          <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} onKeyDown={handleKey} />
          {mode === 'register' && <><label className="input-label">Workspace / tenant</label><input className="input" value={tenantName} onChange={e => setTenantName(e.target.value)} onKeyDown={handleKey} placeholder="Ex: Minha operação" /></>}
          {mode === 'reset' && <><label className="input-label">Token de reset</label><input className="input" value={devToken} onChange={e => setDevToken(e.target.value)} onKeyDown={handleKey} /></>}
          {mode !== 'forgot' && <><label className="input-label">{mode === 'reset' ? 'Nova senha' : t('password')}</label><input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={handleKey} /></>}
          {mode === 'login' && <label className="checkbox-row"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} /> Manter sessão</label>}

          {globalError && <div className="alert alert-error">{globalError}</div>}
          {message && <div className="alert">{message}</div>}
          {devToken && mode !== 'reset' && <div className="hint-card"><strong>Token dev/demo</strong><code>{devToken}</code></div>}

          <button className="btn btn-primary login-btn" disabled={loading} onClick={submit}>
            {loading ? t('entering') : mode === 'login' ? t('enter') : mode === 'register' ? 'Criar conta' : mode === 'forgot' ? 'Gerar reset' : 'Atualizar senha'}
          </button>

          <div className="auth-switcher">
            <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>Login</button>
            <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>Registro</button>
            <button type="button" className={mode === 'forgot' ? 'active' : ''} onClick={() => setMode('forgot')}>Esqueci senha</button>
            <button type="button" className={mode === 'reset' ? 'active' : ''} onClick={() => setMode('reset')}>Reset</button>
          </div>

          <div className="hint-card">
            <strong>Credenciais demo</strong>
            <code>admin@matchflow.local / admin123</code>
            <code>demo@matchflow.local / demo123</code>
          </div>
          <p className="login-footnote">Email verification estruturado, mas desabilitado por padrão. {t('noAutoBet')} {t('manualRequired')}</p>
        </div>
      </div>
    </div>
  );
}
