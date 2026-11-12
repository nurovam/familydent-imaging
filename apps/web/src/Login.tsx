import { useState, type FormEvent } from 'react';
import { api, errorText } from './api';
import { TotpQr } from './TotpQr';

export function Login({ onLogin }: { onLogin: () => void }) {
  const [step, setStep] = useState<'password' | 'totp'>('password');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [secret, setSecret] = useState('');
  const [uri, setUri] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true);
    try {
      if (step === 'password') {
        const next = await api<{ next: string }>('/auth/password', { method: 'POST', body: { email, password } });
        setPassword('');
        if (next.next === 'enroll_totp') {
          const enrollment = await api<{ secret: string; provisioning_uri: string }>('/auth/totp/enroll', { method: 'POST' });
          setSecret(enrollment.secret);
          setUri(enrollment.provisioning_uri);
        } else { setSecret(''); setUri(''); }
        setStep('totp');
      } else {
        await api('/auth/totp', { method: 'POST', body: { code } });
        setSecret(''); setUri(''); setCode(''); onLogin();
      }
    } catch (e) { setError(errorText(e)); setCode(''); }
    finally { setBusy(false); }
  }
  return <main className="auth-page">
    <section className="auth-story"><a className="brand" href="/login"><img src="/assets/logo.svg" alt="Family diagnostic" /></a><div><div className="auth-rule" /><h1>Точная картина.<br />Бережный подход.</h1><p>Исследования ваших пациентов — в одном защищённом пространстве.</p></div><footer>FamilyDent · Цифровая диагностика<br />Душанбе</footer></section>
    <section className="auth-form"><div className="auth-box"><h2>{step === 'password' ? 'Вход в портал' : secret ? 'Подключите аутентификатор' : 'Подтвердите вход'}</h2>
      <p>{step === 'password' ? 'Персональный аккаунт выдаёт сотрудник FamilyDent.' : 'Введите текущий шестизначный код из приложения-аутентификатора.'}</p>
      <form onSubmit={submit}>
        {step === 'password' ? <><label className="field">Электронная почта<input type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required maxLength={254} /></label><label className="field">Пароль<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required maxLength={128} /></label></> : <>
          {secret && <div className="info-box"><p>Откройте приложение-аутентификатор и отсканируйте QR-код.</p>{uri && <TotpQr uri={uri} />}<p>Если сканирование недоступно, добавьте ключ вручную: TOTP, 6 цифр, интервал 30 секунд.</p><label className="field">Ключ настройки<input readOnly value={secret} aria-label="Ключ настройки TOTP" /></label><p>Сохраните ключ в аутентификаторе и подтвердите настройку кодом. После входа ключ больше не показывается.</p></div>}
          <label className="field">Код аутентификатора<input className="code-input" autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e => setCode(e.target.value)} required /></label></>}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn dark" disabled={busy} type="submit">{busy ? 'Подождите…' : step === 'password' ? 'Продолжить' : 'Подтвердить вход'}</button>
        {step === 'totp' && <button className="btn ghost" type="button" disabled={busy} onClick={() => { setStep('password'); setSecret(''); setUri(''); setCode(''); setError(''); }}>Начать заново</button>}
      </form><p className="auth-note">Локальный тестовый стенд. Не вводите реальные медицинские данные. Восстановление доступа — через уполномоченного сотрудника.</p>
    </div></section>
  </main>;
}
