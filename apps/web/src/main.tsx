import { useState } from 'react';
import { filterStudies, studies, type Study } from './studies';
import './design.css';
import './local.css';

export function DemoApp() {
  const [query, setQuery] = useState('');
  const [modality, setModality] = useState('all');
  const [status, setStatus] = useState('all');
  const [menu, setMenu] = useState(false);
  const [selected, setSelected] = useState<Study | null>(null);
  const rows = filterStudies(studies, query, modality, status);
  return <div className="app">
    <aside className={`sidebar ${menu ? 'mobile-open' : ''}`}>
      <a className="brand" href="/" aria-label="FamilyDent — исследования"><img src="/assets/logo.svg" alt="Family diagnostic" /></a>
      <div className="brand-sub">Цифровая диагностика</div><div className="side-label">Рабочее пространство</div>
      <nav className="side-nav" aria-label="Основная навигация"><a className="active" href="/">Исследования</a></nav>
      <div className="sidebar-foot"><div className="help-box">Демонстрационный стенд<p>Только синтетические данные. Серверная авторизация пока не подключена.</p></div></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="row"><button className="icon-btn mobile-menu" aria-label="Открыть меню" aria-expanded={menu} onClick={() => setMenu(!menu)}>☰</button><div className="breadcrumb">Портал диагностики <span> / Исследования</span></div></div><span className="clinic">FamilyDent</span></header>
      <main className="content"><div className="notice demo-notice">Синтетическая демонстрация интерфейса. Не вводите медицинские данные.</div>
        <header className="page-head"><div><div className="eyebrow muted">Кабинет врача</div><h1>Мои исследования</h1><p>Исследования, назначенные лечащему врачу.</p></div></header>
        <section className="panel" aria-label="Список исследований">
          <div className="tabs" aria-label="Статус исследования">{[['all','Все'],['new','Новые'],['viewed','Просмотренные']].map(([value,label]) => <button key={value} aria-pressed={status === value} onClick={() => setStatus(value)}>{label}</button>)}</div>
          <div className="filters"><label className="search"><span className="sr-only">Поиск по пациенту или ID</span><input type="search" value={query} placeholder="Поиск по пациенту или ID" onChange={e => setQuery(e.target.value)} /></label><select aria-label="Тип исследования" value={modality} onChange={e => setModality(e.target.value)}><option value="all">Все типы</option>{['CBCT','OPG','IO'].map(m => <option key={m}>{m}</option>)}</select></div>
          <div className="table-wrap"><table><thead><tr><th>Пациент</th><th>Исследование</th><th>Дата</th><th>Статус</th><th>Действие</th></tr></thead><tbody>{rows.map(s => <tr key={s.id}><td><div className="patient-cell"><span className="avatar">ТП</span><div>{s.name}<small>{s.id}</small></div></div></td><td data-label="Исследование"><span className="modality">{s.modality}</span><p>{s.title}</p></td><td data-label="Дата" className="mono">{s.date}</td><td data-label="Статус"><span className={`badge ${s.fresh ? 'good' : 'neutral'}`}>{s.fresh ? 'Новое' : 'Просмотрено'}</span></td><td data-label="Действие"><button className="open-row" aria-label={`Открыть ${s.id}`} onClick={() => setSelected(s)}>↗</button></td></tr>)}</tbody></table></div>
          {rows.length === 0 && <p className="empty" role="status">Исследования не найдены</p>}<div className="table-bottom" aria-live="polite">Показано {rows.length} из {studies.length}</div>
        </section>
        {selected && <section className="panel panel-pad study-details" aria-label="Об исследовании"><div className="row between"><h2>{selected.title}</h2><button className="btn" onClick={() => setSelected(null)}>Закрыть</button></div><p>{selected.name} · {selected.id}</p><p className="muted">Просмотр DICOM и скачивание появятся после подключения защищённого backend. Реальных файлов здесь нет.</p></section>}
        <footer className="page-footer">© FamilyDent · Цифровая диагностика</footer>
      </main>
    </div>
  </div>;
}
