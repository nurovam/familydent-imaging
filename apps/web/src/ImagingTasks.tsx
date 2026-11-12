import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError, errorText, type ServerStudy } from './api';

type ImportJob = { id: string; state: string; study_uid: string | null; instances: number; error_code: string | null };
const states: Record<string, string> = { QUEUED: 'В очереди на проверку', REVIEW: 'Ожидает подтверждения', FAILED: 'Проверка не пройдена', PUBLISHED: 'Доступно врачу' };
const failures: Record<string, string> = { PATIENT_MISMATCH: 'ID пациента в DICOM не совпадает с выбранной записью.', MIXED_STUDIES: 'Архив содержит разные исследования.', UNSAFE_ARCHIVE: 'Небезопасный архив. Проверьте его содержимое.', UNSUPPORTED_DICOM: 'Этот формат DICOM пока не поддерживается.', STUDY_UID_CONFLICT: 'UID уже связан с другим исследованием.', STUDY_UID_MISMATCH: 'UID не совпадает с зарегистрированным исследованием.' };

export function ImportTask({ study, csrf, onPublished }: { study: ServerStudy; csrf: string; onPublished: () => Promise<void> }) {
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const reload = useCallback(async () => setJobs(await api<ImportJob[]>(`/staff/studies/${study.id}/imports`)), [study.id]);
  useEffect(() => { const controller = new AbortController(); api<ImportJob[]>(`/staff/studies/${study.id}/imports`, { signal: controller.signal }).then(setJobs).catch(e => { if (!controller.signal.aborted) setMessage(errorText(e)); }); return () => controller.abort(); }, [study.id]);
  useEffect(() => { if (!jobs.some(j => j.state === 'QUEUED')) return; const timer = setInterval(() => { reload().catch(e => setMessage(errorText(e))); }, 2000); return () => clearInterval(timer); }, [jobs, reload]);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const file = new FormData(form).get('dicom');
    if (!(file instanceof File) || !file.size) return;
    if (file.size > 32 * 1024 * 1024) { setMessage('Файл превышает 32 МиБ.'); return; }
    setBusy(true); setMessage('');
    try {
      const response = await fetch(`/api/staff/studies/${study.id}/imports`, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRF-Token': csrf, 'Content-Type': file.name.toLowerCase().endsWith('.zip') ? 'application/zip' : 'application/dicom' }, body: file });
      if (!response.ok) throw new ApiError(response.status, 'IMPORT_FAILED');
      const queued: ImportJob = await response.json();
      setJobs(current => [queued, ...current]); form.reset(); await reload();
    } catch (e) { setMessage(errorText(e)); } finally { setBusy(false); }
  }
  const active = jobs.find(j => j.state === 'REVIEW');
  return <section className="panel panel-pad task-panel"><h2>Импорт DICOM</h2><p>{study.title} · {study.local_identifier}</p><p className="form-intro">Только синтетические снимки. Один DICOM или ZIP, до 32 МиБ. Файлы станут доступны врачу после проверки и подтверждения.</p>
    {study.state === 'REGISTERED' && !jobs.some(j => ['QUEUED', 'REVIEW', 'PUBLISHED'].includes(j.state)) && <form className="stack task-form" onSubmit={upload}><label className="field">DICOM или ZIP<input name="dicom" type="file" accept=".dcm,.dicom,.zip" required /></label><button className="btn primary" disabled={busy}>{busy ? 'Загрузка…' : 'Загрузить на проверку'}</button></form>}
    {jobs.map(job => <div key={job.id} className="import-status"><strong>{states[job.state]}</strong>{job.state === 'FAILED' && <p>{failures[job.error_code ?? ''] ?? 'Файл не прошёл проверку. Проверьте DICOM и ограничения импорта.'}</p>}{job.study_uid && <p className="dicom-uid">Study UID: {job.study_uid}<br />Файлов: {job.instances}</p>}</div>)}
    {active && <div className="stack"><label className="review-confirm"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Подтверждаю: файлы относятся к пациенту {study.local_identifier} и этому исследованию.</label><button className="btn primary" disabled={!confirmed || busy} onClick={async () => { setBusy(true); try { await api(`/staff/studies/${study.id}/imports/${active.id}/publish`, { method: 'POST', csrf, body: { confirmed: true } }); await reload(); await onPublished(); } catch (e) { setMessage(errorText(e)); } finally { setBusy(false); } }}>Подтвердить исследование</button></div>}
    <p className="form-feedback" role="status">{message}</p></section>;
}

type Imaging = { viewer_url: string; zip_url: string; instances: { id: string }[] };
export function DoctorImaging({ study }: { study: ServerStudy }) {
  const [data, setData] = useState<Imaging | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { if (study.state !== 'READY') return; const controller = new AbortController(); api<Imaging>(`/doctor/studies/${study.id}/imaging`, { signal: controller.signal }).then(setData).catch(e => { if (!controller.signal.aborted) setError(errorText(e)); }); return () => controller.abort(); }, [study.id, study.state]);
  if (study.state !== 'READY') return <p className="muted">Снимки ещё не подтверждены сотрудником. Просмотр и скачивание пока недоступны.</p>;
  return <>{error && <p className="error" role="alert">{error}</p>}{data && <><p className="muted">Синтетическое исследование · {data.instances.length} файлов. Тестовый просмотр, не для диагностики.</p><div className="workbench-actions"><a className="btn primary" href={data.viewer_url} target="_blank" rel="noreferrer">Открыть просмотр</a><a className="btn" href={data.zip_url} download>Скачать DICOM</a></div></>}</>;
}
