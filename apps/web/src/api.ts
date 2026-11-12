export type Account = { id: string; display_name: string; role: 'doctor' | 'imaging_staff' | 'platform_admin'; csrf_token: string };
export type ServerStudy = { id: string; patient_id: string; local_identifier: string; display_name: string; title: string; modality: string; state: string; created_at: string };
export type Page<T> = { items: T[]; total: number; limit: number; offset: number };
export type Clinic = { id: string; name: string };
export type Doctor = { id: string; display_name: string; clinic_id: string };

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string) { super(code); this.status = status; this.code = code; }
}

export async function api<T>(path: string, options: { method?: string; body?: unknown; csrf?: string; signal?: AbortSignal } = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: options.method ?? 'GET', credentials: 'same-origin', signal: options.signal,
    headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.csrf ? { 'X-CSRF-Token': options.csrf } : {}) },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    let code = 'SERVICE_UNAVAILABLE';
    try { code = (await response.json()).code ?? code; } catch { /* Reverse proxy may return an empty 502. */ }
    throw new ApiError(response.status, code);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return 'Слишком много попыток. Повторите через 15 минут.';
    if (error.status === 401) return 'Проверьте данные или повторите вход. Код мог истечь или уже использоваться.';
    if (error.status === 403) return 'Действие недоступно. Обновите страницу и проверьте права доступа.';
    if (error.status === 409) return 'Запись уже существует или состояние изменилось. Обновите данные.';
    if (error.status === 422) return 'Проверьте заполнение полей.';
  }
  return 'Сервис временно недоступен. Попробуйте ещё раз.';
}
