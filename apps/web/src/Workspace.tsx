import { UiIcon, initials } from './UiIcon';
import { DoctorImaging, ImportTask } from './ImagingTasks';
import { TaskDialog } from './TaskDialog';
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
  return <div className="app clinical-workspace"><aside className={`sidebar ${menu ? 'mobile-open' : ''}`}><a className="brand" href="/"><img src="/assets/logo.svg" alt="Family diagnostic" /></a><div className="brand-sub">Цифровая диагностика</div><div className="side-label">Рабочее пространство</div><nav className="side-nav" aria-label="Основная навигация"><a className="active" href="/" aria-current="page"><UiIcon name={account.role === 'platform_admin' ? 'users' : 'studies'} /><span>{account.role === 'platform_admin' ? 'Команда и доступы' : 'Исследования'}</span></a></nav><div className="sidebar-foot"><div className="side-user"><span className="avatar" aria-hidden="true">{initials(account.display_name)}</span><div><strong>{account.display_name}</strong><span>{roleName}</span></div></div></div></aside>
    <div className="workspace"><header className="topbar"><div className="row"><button className="icon-btn mobile-menu" onClick={() => setMenu(!menu)} aria-expanded={menu} aria-label="Открыть меню"><UiIcon name="menu" /></button><div className="breadcrumb">Портал диагностики <span> / {roleName}</span></div></div><button className="btn logout-button" type="button" disabled={loggingOut} aria-busy={loggingOut} onClick={logout}><UiIcon name="logout" />{loggingOut ? 'Выходим…' : 'Выйти'}</button></header>
      <main className="content"><p className="environment-note">Тестовый режим · Только синтетические данные</p>{error && <p className="error" role="alert">{error}</p>}
        {account.role === 'doctor' ? <DoctorStudies report={report} /> : account.role === 'imaging_staff' ? <Staff account={account} report={report} /> : <Admin account={account} report={report} />}
        <footer className="page-footer"><span>© FamilyDent · Цифровая диагностика</span><span className="access-note"><UiIcon name="shield" />Персональный доступ</span></footer>
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
  return <><header className="page-head"><div><h1>Мои исследования</h1><p>Только исследования, назначенные вам сотрудником FamilyDent.</p></div><button className="btn" onClick={() => setVersion(v => v + 1)}><UiIcon name="refresh" />Обновить</button></header>
    <section className="panel study-register" aria-label="Назначенные исследования"><div className="panel-head"><h2>Назначенные исследования</h2>{page && <span className="register-count">{page.total}</span>}</div><div className="filters"><label className="search"><UiIcon name="search" /><span className="sr-only">Поиск по пациенту или ID</span><input type="search" maxLength={160} placeholder="Поиск по пациенту или ID" value={query} onChange={e => { setQuery(e.target.value); setOffset(0); }} /></label></div>
      {loading && <p className="empty" role="status">Загрузка…</p>}{page && <><StudyTable studies={page.items} onOpen={open} />{page.items.length === 0 && <p className="empty">Назначенные исследования не найдены</p>}<div className="table-bottom"><span>Найдено: {page.total}</span><div className="row"><button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}>Назад</button><button className="btn" disabled={offset + 25 >= page.total} onClick={() => setOffset(offset + 25)}>Далее</button></div></div></>}
    </section>{selected && <section className="panel panel-pad study-details"><h2>{selected.title}</h2><p>{selected.display_name} · {selected.local_identifier}</p><DoctorImaging key={selected.id} study={selected} /><button className="btn" onClick={() => setSelected(null)}>Закрыть</button></section>}</>;
}

function StudyTable({ studies, onOpen }: { studies: ServerStudy[]; onOpen: (id: string) => void }) {
  return <div className="table-wrap"><table><thead><tr><th>Пациент</th><th>Исследование</th><th>Дата</th><th>Статус</th><th>Действие</th></tr></thead><tbody>{studies.map(s => <tr key={s.id}><td><div className="patient-cell"><span className="avatar" aria-hidden="true">{initials(s.display_name)}</span><div><strong>{s.display_name}</strong><small>{s.local_identifier}</small></div></div></td><td data-label="Исследование"><span className="modality">{s.modality}</span><p>{s.title}</p></td><td data-label="Дата" className="study-date"><time dateTime={s.created_at}>{new Date(s.created_at).toLocaleDateString('ru-RU')}</time></td><td data-label="Статус"><span className={`badge ${s.state === 'READY' ? 'good' : s.state === 'BLOCKED' ? 'danger' : 'pending'}`}><span className="dot" aria-hidden="true" />{stateNames[s.state]}</span></td><td data-label="Действие"><button className="open-row" aria-label={`Открыть ${s.local_identifier}`} onClick={() => onOpen(s.id)}><UiIcon name="open" /></button></td></tr>)}</tbody></table></div>;
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
  return <section className={`panel panel-pad task-panel ${className}`}><h2>{title}</h2><form className="stack task-form" onSubmit={onSubmit}>{children}<button className="btn primary task-submit" disabled={busy}>{busy ? 'Подождите…' : 'Сохранить'}</button><p className={`form-feedback ${message === 'Сохранено' ? 'is-success' : message ? 'is-error' : ''}`} role="status">{message && <UiIcon name={message === 'Сохранено' ? 'check' : 'shield'} />}{message}</p></form></section>;
}
function Field({ name, label, type = 'text', maxLength = 160 }: { name: string; label: string; type?: string; maxLength?: number }) {
  return <label className="field">{label}<input name={name} type={type} required maxLength={maxLength} autoComplete={type === 'password' ? 'new-password' : 'off'} /></label>;
}

function Staff({ account, report }: { account: Account; report: Report }) {
  const [task, setTask] = useState<'patient' | 'study' | 'account' | null>(null);
  const [rows, setRows] = useState<ServerStudy[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selected, setSelected] = useState('');
  const [importing, setImporting] = useState<ServerStudy | null>(null);
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
  return <><header className="page-head"><div><h1>Исследования</h1><p>Регистрация, импорт снимков и назначения врачам.</p></div>
    <div className="workbench-actions page-actions" aria-label="Действия с исследованиями"><button className="btn primary" onClick={() => setTask('study')}><UiIcon name="plus" />Новое исследование</button><button className="btn" onClick={() => setTask('patient')}>Новый пациент</button><button className="btn" onClick={() => setTask('account')}>Добавить врача</button></div></header>
    <div className="workbench-list"><section className="panel study-register"><div className="panel-head"><h2>Последние исследования</h2><button className="btn" onClick={() => reload().catch(report)}><UiIcon name="refresh" />Обновить</button></div><StudyTable studies={rows} onOpen={id => void open(id)} />{rows.length === 0 && <p className="empty">Исследований пока нет. Зарегистрируйте первое исследование.</p>}</section></div>
    {task === 'patient' && <TaskDialog title="Зарегистрировать пациента" onClose={() => setTask(null)}><TaskForm title="Зарегистрировать пациента" submit={async data => {
      const created = await api<{ id: string }>('/staff/patients', { method: 'POST', csrf, body: { local_identifier: data.get('identifier'), display_name: data.get('name') } }); setPatient({ id: created.id, local_identifier: String(data.get('identifier')), display_name: String(data.get('name')) }); setPatientQuery(String(data.get('identifier')));
    }}><Field name="identifier" label="Внутренний ID пациента" maxLength={80} /><Field name="name" label="ФИО пациента" />{patient && <p>Выбрана запись: {patient.local_identifier} · {patient.display_name}</p>}</TaskForm></TaskDialog>}
    {task === 'study' && <TaskDialog title="Зарегистрировать исследование" onClose={() => setTask(null)}><TaskForm title="Зарегистрировать исследование" submit={async data => {
      if (!patient) throw new ApiError(422, 'PATIENT_REQUIRED');
      await api('/staff/studies', { method: 'POST', csrf, body: { patient_id: data.get('patient'), title: data.get('title'), modality: data.get('modality') } }); await reload();
    }}><label className="field">Внутренний ID для выбора записи<input value={patientQuery} maxLength={80} onChange={e => { setPatientQuery(e.target.value); setPatient(null); setPatientMessage(''); }} /></label><button className="btn" type="button" onClick={async () => { try { const found = await api<PatientRecord[]>(`/staff/patients?local_identifier=${encodeURIComponent(patientQuery)}`); setPatient(found[0] ?? null); setPatientMessage(found.length ? '' : 'Запись не найдена. Проверьте внутренний ID.'); } catch (e) { report(e); } }}>Найти запись</button>{patientMessage && <p role="status">{patientMessage}</p>}{patient && <p>Пациент исследования: {patient.local_identifier} · {patient.display_name}</p>}<input type="hidden" name="patient" value={patient?.id ?? ''} /><Field name="title" label="Исследование" maxLength={200} /><label className="field">Тип исследования<select name="modality"><option>CBCT</option><option>OPG</option><option>IO</option></select></label></TaskForm></TaskDialog>}
    {selected && <TaskDialog title="Назначить врачу" onClose={() => setSelected('')}><TaskForm title="Назначить врачу" submit={async data => {
      const person = doctors.find(d => `${d.id}:${d.clinic_id}` === data.get('doctor')); if (!person) throw new Error();
      await api(`/staff/studies/${selected}/assignments`, { method: 'POST', csrf, body: { doctor_id: person.id, clinic_id: person.clinic_id } }); await open(selected);
    }}><p>{rows.find(s => s.id === selected)?.title} · {rows.find(s => s.id === selected)?.local_identifier}</p><button className="btn" type="button" onClick={() => { const study = rows.find(s => s.id === selected); if (study) { setSelected(''); setImporting(study); } }}><UiIcon name="upload" />Импорт DICOM</button><label className="field">Врач<select name="doctor" required><option value="">Выберите врача</option>{doctors.map(d => <option key={`${d.id}:${d.clinic_id}`} value={`${d.id}:${d.clinic_id}`}>{d.display_name}</option>)}</select></label>{grants.map(g => <div key={g.id} className="row between"><span>{g.doctor} · {g.revoked ? 'Отозвано' : 'Назначено'}</span>{!g.revoked && <button className="btn" type="button" onClick={async () => { try { await api(`/staff/assignments/${g.id}/revoke`, { method: 'POST', csrf }); await open(selected); } catch (e) { report(e); } }}>Отозвать</button>}</div>)}</TaskForm></TaskDialog>}
    {importing && <TaskDialog title="Импорт DICOM" onClose={() => setImporting(null)}><ImportTask study={importing} csrf={csrf} onPublished={async () => { await reload(); setImporting({ ...importing, state: 'READY' }); }} /></TaskDialog>}
    {task === 'account' && <TaskDialog title="Создать проверенный аккаунт" onClose={() => setTask(null)}><AccountForm account={account} report={report} onSaved={reload} /></TaskDialog>}</>;
}

function AccountForm({ account, report, onSaved }: { account: Account; report: Report; onSaved: () => Promise<void> }) {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  useEffect(() => { api<Clinic[]>('/clinics').then(setClinics).catch(report); }, [report]);
  return <TaskForm className="account-creation" title="Создать проверенный аккаунт" submit={async data => {
    await api('/admin/users', { method: 'POST', csrf: account.csrf_token, body: { email: data.get('email'), display_name: data.get('name'), role: data.get('role'), password: data.get('password'), clinic_id: data.get('clinic') || null } }); await onSaved();
  }}><p className="form-intro">Создавайте аккаунт только после проверки врача или сотрудника. При первом входе потребуется подключить TOTP.</p><Field name="name" label="ФИО" /><Field name="email" label="Email" type="email" maxLength={254} /><Field name="password" label="Начальный пароль (от 12 символов)" type="password" maxLength={128} /><label className="field">Роль<select name="role"><option value="doctor">Врач</option>{account.role === 'platform_admin' && <option value="imaging_staff">Сотрудник</option>}</select></label><label className="field">Клиника (обязательна для врача)<select name="clinic"><option value="">Без клиники</option>{clinics.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label></TaskForm>;
}

function Admin({ account, report }: { account: Account; report: Report }) {
  const [task, setTask] = useState<'clinic' | 'account' | null>(null);
  const [users, setUsers] = useState<{ id: string; display_name: string; role: string; active: boolean }[]>([]);
  const reload = useCallback(async () => { setUsers(await api('/admin/users')); }, []);
  useEffect(() => { reload().catch(report); }, [reload, report]);
  return <><header className="page-head"><div><h1>Команда и доступы</h1><p>Персональные аккаунты и доступ к порталу.</p></div>
    <div className="workbench-actions page-actions" aria-label="Управление командой"><button className="btn primary" onClick={() => setTask('account')}><UiIcon name="plus" />Добавить аккаунт</button><button className="btn" onClick={() => setTask('clinic')}>Добавить клинику</button><button className="btn" onClick={() => reload().catch(report)}><UiIcon name="refresh" />Обновить</button></div></header>
    {task === 'clinic' && <TaskDialog title="Добавить клинику" onClose={() => setTask(null)}><TaskForm title="Добавить клинику" submit={async data => { await api('/admin/clinics', { method: 'POST', csrf: account.csrf_token, body: { name: data.get('name') } }); }}><Field name="name" label="Название клиники" /></TaskForm></TaskDialog>}
    {task === 'account' && <TaskDialog title="Создать проверенный аккаунт" onClose={() => setTask(null)}><AccountForm account={account} report={report} onSaved={reload} /></TaskDialog>}
    <section className="panel account-register" aria-label="Аккаунты"><div className="table-wrap"><table><thead><tr><th>Сотрудник</th><th>Роль</th><th>Доступ</th><th>Действие</th></tr></thead><tbody>{users.map(u => <tr key={u.id}><td><div className="patient-cell"><span className="avatar" aria-hidden="true">{initials(u.display_name)}</span><strong>{u.display_name}</strong></div></td><td data-label="Роль">{roleNames[u.role]}</td><td data-label="Доступ"><span className={`badge ${u.active ? 'good' : 'neutral'}`}>{u.active ? 'Активен' : 'Отключён'}</span></td><td data-label="Действие">{u.active && u.id !== account.id && <button className="btn" onClick={async () => { if (!window.confirm('Отключить аккаунт и отозвать его доступы?')) return; try { await api(`/admin/users/${u.id}/disable`, { method: 'POST', csrf: account.csrf_token }); await reload(); } catch (e) { report(e); } }}>Отключить</button>}</td></tr>)}</tbody></table></div></section></>;
}
