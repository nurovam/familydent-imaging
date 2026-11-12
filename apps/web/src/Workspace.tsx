import { useCallback, useEffect, useState, useRef, type FormEvent, type ReactNode } from 'react';
import './workspace.css';
import { ApiError, api, errorText, type Account, type Clinic, type Doctor, type Page, type ServerStudy } from './api';

export function Workspace({ account, onSessionEnd }: { account: Account; onSessionEnd: () => void }) {
  const [menu, setMenu] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [error, setError] = useState('');
  const report = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) onSessionEnd();
    else setError(errorText(e));
  }, [onSessionEnd]);
  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try { await api('/auth/logout', { method: 'POST', csrf: account.csrf_token }); onSessionEnd(); }
    catch (e) { report(e); }
    finally { setLoggingOut(false); }
  }
  const roleName = account.role === 'doctor' ? 'Кабинет врача' : account.role === 'imaging_staff' ? 'Кабинет сотрудника' : 'Управление аккаунтами';
  return <div className="app clinical-workspace"><aside className={`sidebar ${menu ? 'mobile-open' : ''}`}><a className="brand" href="/"><img src="/assets/logo.svg" alt="Family diagnostic" /></a><div className="brand-sub">Цифровая диагностика</div><div className="side-label">Рабочее пространство</div><nav className="side-nav"><a className="active" href="/">{roleName}</a></nav><div className="sidebar-foot"><div className="help-box">{account.display_name}<p>{roleName}</p></div></div></aside>
    <div className="workspace"><header className="topbar"><div className="row"><button className="icon-btn mobile-menu" onClick={() => setMenu(!menu)} aria-expanded={menu} aria-label="Открыть меню">☰</button><div className="breadcrumb">Портал диагностики <span> / {roleName}</span></div></div><button className="btn logout-button" type="button" disabled={loggingOut} aria-busy={loggingOut} onClick={logout}><svg className="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 3H3v18h6m4-14 5 5-5 5m-6-5h14" /></svg>{loggingOut ? 'Выходим…' : 'Выйти'}</button></header>
      <main className="content"><div className="notice demo-notice">Тестовый режим · Только синтетические данные.</div>{error && <p className="error" role="alert">{error}</p>}
        {account.role === 'doctor' ? <DoctorStudies report={report} /> : account.role === 'imaging_staff' ? <Staff account={account} report={report} /> : <Admin account={account} report={report} />}
      </main></div></div>;
}

type Report = (error: unknown) => void;
type PatientRecord = { id: string; local_identifier: string; display_name: string };
const stateNames: Record<string, string> = { REGISTERED: 'Зарегистрировано', READY: 'Готово', BLOCKED: 'Заблокировано' };
const roleNames: Record<string, string> = { doctor: 'Врач', imaging_staff: 'Сотрудник', platform_admin: 'Администратор' };
function DoctorStudies({ report }: { report: Report }) {
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<Page<ServerStudy> | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<ServerStudy | null>(null);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setSelected(null); setLoading(true);
    api<Page<ServerStudy>>(`/doctor/studies?q=${encodeURIComponent(query)}&offset=${offset}&limit=25`, { signal: controller.signal })
      .then(setPage).catch(e => { if (!controller.signal.aborted) report(e); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, offset, version, report]);
  async function open(id: string) {
    setSelected(null);
    try { setSelected(await api<ServerStudy>(`/doctor/studies/${id}`)); } catch (e) { report(e); }
  }
  return <><header className="page-head"><div><div className="eyebrow muted">Кабинет врача</div><h1>Мои исследования</h1><p>Только исследования, назначенные вам сотрудником FamilyDent.</p></div><button className="btn" onClick={() => setVersion(v => v + 1)}>Обновить</button></header>
    <section className="panel"><div className="filters"><label className="search"><span className="sr-only">Поиск по пациенту или ID</span><input type="search" maxLength={160} placeholder="Поиск по пациенту или ID" value={query} onChange={e => { setQuery(e.target.value); setOffset(0); }} /></label></div>
      {loading && <p className="empty" role="status">Загрузка…</p>}{page && <><StudyTable studies={page.items} onOpen={open} />{page.items.length === 0 && <p className="empty">Назначенные исследования не найдены</p>}<div className="table-bottom"><span>Найдено: {page.total}</span><div className="row"><button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}>Назад</button><button className="btn" disabled={offset + 25 >= page.total} onClick={() => setOffset(offset + 25)}>Далее</button></div></div></>}
    </section>{selected && <section className="panel panel-pad study-details"><h2>{selected.title}</h2><p>{selected.display_name} · {selected.local_identifier}</p><p className="muted">Статус: {stateNames[selected.state]}. Просмотр и скачивание DICOM будут подключены после защищённого импорта.</p><button className="btn" onClick={() => setSelected(null)}>Закрыть</button></section>}</>;
}

function StudyTable({ studies, onOpen }: { studies: ServerStudy[]; onOpen: (id: string) => void }) {
  return <div className="table-wrap"><table><thead><tr><th>Пациент</th><th>Исследование</th><th>Дата</th><th>Статус</th><th>Действие</th></tr></thead><tbody>{studies.map(s => <tr key={s.id}><td><div className="patient-cell"><div>{s.display_name}<small>{s.local_identifier}</small></div></div></td><td data-label="Исследование"><span className="modality">{s.modality}</span><p>{s.title}</p></td><td data-label="Дата">{new Date(s.created_at).toLocaleDateString('ru-RU')}</td><td data-label="Статус"><span className="badge neutral">{stateNames[s.state]}</span></td><td data-label="Действие"><button className="open-row" aria-label={`Открыть ${s.local_identifier}`} onClick={() => onOpen(s.id)}>↗</button></td></tr>)}</tbody></table></div>;
}

function TaskForm({ title, submit, children, className = '' }: { title: string; submit: (data: FormData) => Promise<void>; children: ReactNode; className?: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form = e.currentTarget; setBusy(true); setMessage('');
    try { await submit(new FormData(form)); form.reset(); setMessage('Сохранено'); }
    catch (error) { setMessage(errorText(error)); }
    finally { setBusy(false); }
  }
  return <section className={`panel panel-pad task-panel ${className}`}><h2>{title}</h2><form className="stack task-form" onSubmit={onSubmit}>{children}<button className="btn primary task-submit" disabled={busy}>{busy ? 'Подождите…' : 'Сохранить'}</button><p className="form-feedback" role="status">{message}</p></form></section>;
}
function Field({ name, label, type = 'text', maxLength = 160 }: { name: string; label: string; type?: string; maxLength?: number }) {
  return <label className="field">{label}<input name={name} type={type} required maxLength={maxLength} autoComplete={type === 'password' ? 'new-password' : 'off'} /></label>;
}

function Staff({ account, report }: { account: Account; report: Report }) {
  const [rows, setRows] = useState<ServerStudy[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selected, setSelected] = useState('');
  const [grants, setGrants] = useState<{ id: string; doctor: string; revoked: boolean }[]>([]);
  const [patient, setPatient] = useState<PatientRecord | null>(null);
  const [patientQuery, setPatientQuery] = useState('');
  const [patientMessage, setPatientMessage] = useState('');
  const opening = useRef(0);
  const csrf = account.csrf_token;
  const reload = useCallback(async () => {
    const [page, people] = await Promise.all([api<Page<ServerStudy>>('/staff/studies'), api<Doctor[]>('/staff/doctors')]);
    setRows(page.items); setDoctors(people);
  }, []);
  useEffect(() => { reload().catch(report); }, [reload, report]);
  async function open(id: string) { const version = ++opening.current; setSelected(''); setGrants([]); try { const result = await api<{ id: string; doctor: string; revoked: boolean }[]>(`/staff/studies/${id}/assignments`); if (version === opening.current) { setGrants(result); setSelected(id); } } catch (e) { report(e); } }
  return <><header className="page-head"><div><div className="eyebrow muted">Кабинет сотрудника</div><h1>Регистрация и назначения</h1><p>В этом этапе создаются метаданные. Загрузка файлов ещё не подключена.</p></div></header>
    <div className="workspace-grid staff-grid"><TaskForm title="Зарегистрировать пациента" submit={async data => {
      const created = await api<{ id: string }>('/staff/patients', { method: 'POST', csrf, body: { local_identifier: data.get('identifier'), display_name: data.get('name') } }); setPatient({ id: created.id, local_identifier: String(data.get('identifier')), display_name: String(data.get('name')) }); setPatientQuery(String(data.get('identifier')));
    }}><Field name="identifier" label="Внутренний ID пациента" maxLength={80} /><Field name="name" label="ФИО пациента" />{patient && <p>Выбрана запись: {patient.local_identifier} · {patient.display_name}</p>}</TaskForm>
    <TaskForm title="Зарегистрировать исследование" submit={async data => {
      if (!patient) throw new ApiError(422, 'PATIENT_REQUIRED');
      await api('/staff/studies', { method: 'POST', csrf, body: { patient_id: data.get('patient'), title: data.get('title'), modality: data.get('modality') } }); await reload();
    }}><label className="field">Внутренний ID для выбора записи<input value={patientQuery} maxLength={80} onChange={e => { setPatientQuery(e.target.value); setPatient(null); setPatientMessage(''); }} /></label><button className="btn" type="button" onClick={async () => { try { const found = await api<PatientRecord[]>(`/staff/patients?local_identifier=${encodeURIComponent(patientQuery)}`); setPatient(found[0] ?? null); setPatientMessage(found.length ? '' : 'Запись не найдена. Проверьте внутренний ID.'); } catch (e) { report(e); } }}>Найти запись</button>{patientMessage && <p role="status">{patientMessage}</p>}{patient && <p>Пациент исследования: {patient.local_identifier} · {patient.display_name}</p>}<input type="hidden" name="patient" value={patient?.id ?? ''} /><Field name="title" label="Исследование" maxLength={200} /><label className="field">Тип исследования<select name="modality"><option>CBCT</option><option>OPG</option><option>IO</option></select></label></TaskForm>
    <section className="panel workspace-wide"><div className="panel-head"><h2>Последние исследования</h2><button className="btn" onClick={() => reload().catch(report)}>Обновить</button></div><StudyTable studies={rows} onOpen={id => void open(id)} />{rows.length === 0 && <p className="empty">Исследований пока нет</p>}</section>
    {selected && <TaskForm className="workspace-wide" title="Назначить врачу" submit={async data => {
      const person = doctors.find(d => `${d.id}:${d.clinic_id}` === data.get('doctor')); if (!person) throw new Error();
      await api(`/staff/studies/${selected}/assignments`, { method: 'POST', csrf, body: { doctor_id: person.id, clinic_id: person.clinic_id } }); await open(selected);
    }}><p>{rows.find(s => s.id === selected)?.title} · {rows.find(s => s.id === selected)?.local_identifier}</p><label className="field">Врач<select name="doctor" required><option value="">Выберите врача</option>{doctors.map(d => <option key={`${d.id}:${d.clinic_id}`} value={`${d.id}:${d.clinic_id}`}>{d.display_name}</option>)}</select></label>{grants.map(g => <div key={g.id} className="row between"><span>{g.doctor} · {g.revoked ? 'Отозвано' : 'Назначено'}</span>{!g.revoked && <button className="btn" type="button" onClick={async () => { try { await api(`/staff/assignments/${g.id}/revoke`, { method: 'POST', csrf }); await open(selected); } catch (e) { report(e); } }}>Отозвать</button>}</div>)}</TaskForm>}
    <AccountForm account={account} report={report} onSaved={reload} /></div></>;
}

function AccountForm({ account, report, onSaved }: { account: Account; report: Report; onSaved: () => Promise<void> }) {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  useEffect(() => { api<Clinic[]>('/clinics').then(setClinics).catch(report); }, [report]);
  return <TaskForm className="account-creation" title="Создать проверенный аккаунт" submit={async data => {
    await api('/admin/users', { method: 'POST', csrf: account.csrf_token, body: { email: data.get('email'), display_name: data.get('name'), role: data.get('role'), password: data.get('password'), clinic_id: data.get('clinic') || null } }); await onSaved();
  }}><p className="form-intro">Создавайте аккаунт только после проверки врача или сотрудника. При первом входе потребуется подключить TOTP.</p><Field name="name" label="ФИО" /><Field name="email" label="Email" type="email" maxLength={254} /><Field name="password" label="Начальный пароль (от 12 символов)" type="password" maxLength={128} /><label className="field">Роль<select name="role"><option value="doctor">Врач</option>{account.role === 'platform_admin' && <option value="imaging_staff">Сотрудник</option>}</select></label><label className="field">Клиника (обязательна для врача)<select name="clinic"><option value="">Без клиники</option>{clinics.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label></TaskForm>;
}

function Admin({ account, report }: { account: Account; report: Report }) {
  const [version, setVersion] = useState(0);
  const [users, setUsers] = useState<{ id: string; display_name: string; role: string; active: boolean }[]>([]);
  const reload = useCallback(async () => { setUsers(await api('/admin/users')); }, []);
  useEffect(() => { reload().catch(report); }, [reload, report]);
  return <><header className="page-head"><div><div className="eyebrow muted">Администрирование</div><h1>Команда и доступы</h1><p>Административная роль не даёт доступа к медицинским исследованиям.</p></div></header><div className="workspace-grid admin-grid">
    <TaskForm title="Добавить клинику" submit={async data => { await api('/admin/clinics', { method: 'POST', csrf: account.csrf_token, body: { name: data.get('name') } }); setVersion(v => v + 1); }}><Field name="name" label="Название клиники" /></TaskForm>
    <AccountForm key={version} account={account} report={report} onSaved={reload} />
    <section className="panel panel-pad workspace-wide"><h2>Аккаунты</h2>{users.map(u => <div className="row between account-row" key={u.id}><span>{u.display_name} · {roleNames[u.role]} · {u.active ? 'Активен' : 'Отключён'}</span>{u.active && u.id !== account.id && <button className="btn" onClick={async () => { if (!window.confirm('Отключить аккаунт и отозвать его доступы?')) return; try { await api(`/admin/users/${u.id}/disable`, { method: 'POST', csrf: account.csrf_token }); await reload(); } catch (e) { report(e); } }}>Отключить</button>}</div>)}</section></div></>;
}
