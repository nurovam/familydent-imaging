import { useEffect, useState } from 'react';
import { api, errorText, type ServerStudy } from './api';
import { DentalSketch } from './DentalSketch';
import { UiIcon } from './UiIcon';

type StudyEvent = { id: string; kind: string; created_at: string; study: ServerStudy };
type Overview = { latest: ServerStudy | null; events: StudyEvent[] };
const eventNames: Record<string, string> = { registered: 'Новое исследование', assigned: 'Назначен доступ врачу', revoked: 'Назначение отозвано', published: 'Снимки готовы к просмотру', viewed: 'Исследование открыто', opened: 'Открыт просмотр снимков', downloaded: 'Запрошено скачивание DICOM' };
function dateTime(value: string) {
  return new Date(value).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
export function StudyContext({ version, selection, onOpen, report }: { version: number; selection: ServerStudy | null; onOpen: (study: ServerStudy) => void; report: (error: unknown) => void }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setOverview(null); setError('');
    api<Overview>('/workspace/overview', { signal: controller.signal }).then(setOverview).catch(e => {
      if (!controller.signal.aborted) { setError(errorText(e)); report(e); }
    });
    return () => controller.abort();
  }, [version, report]);
  const study = selection ?? overview?.latest;
  return <aside className="study-context" aria-label="Последнее исследование и события">
    <article className="panel recent-study" aria-label="Карточка исследования">
      <div className="panel-head"><div><div className="eyebrow">{selection ? 'Выбранное исследование' : 'Последнее поступление'}</div><h3>{study?.title ?? (overview ? 'Исследований пока нет' : error ? 'Данные недоступны' : 'Загрузка…')}</h3></div><UiIcon name="studies" /></div>
      <DentalSketch />
      <div className="details">{study ? <><div className="recent-patient">{study.display_name}</div><p><time dateTime={study.created_at}>{dateTime(study.created_at)}</time> · {study.modality}</p><button className="btn" onClick={() => onOpen(study)}>Открыть исследование<svg className="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5" /></svg></button></> : <p>{error || (overview ? 'Здесь появится последнее доступное вам исследование.' : 'Проверяем доступные исследования.')}</p>}</div>
    </article>
    <section className="panel activity" aria-label="Последние события"><h3>Последние события</h3>
      {overview?.events.map(event => <div className="activity-item" key={event.id}><strong>{eventNames[event.kind]}</strong><p>{event.study.display_name} · {event.study.modality}</p><time className="mono" dateTime={event.created_at}>{dateTime(event.created_at)}</time></div>)}
      {overview?.events.length === 0 && <p className="context-empty">Событий по доступным исследованиям пока нет.</p>}
      {!overview && <p className="context-empty">{error ? 'Не удалось загрузить события. Обновите список.' : 'Загрузка событий…'}</p>}
    </section>
  </aside>;
}
