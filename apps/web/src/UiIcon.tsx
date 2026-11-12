import type { ReactNode } from 'react';

/** Outline vocabulary from the immutable OpenDesign handoff. */
const paths: Record<string, ReactNode> = {
  studies: <><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" /><rect x="7" y="7" width="10" height="10" rx="2" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.9" /><circle cx="9" cy="7" r="4" /><path d="M16 3.1a4 4 0 0 1 0 7.8" /></>,
  upload: <path d="M12 16V3m-5 5 5-5 5 5M3 15v5h18v-5" />,
  download: <path d="M12 3v13m-5-5 5 5 5-5M3 16v5h18v-5" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M6 6a8 8 0 0 1 13 3M18 18a8 8 0 0 1-13-3" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  open: <path d="M7 17 17 7M7 7h10v10" />,
  logout: <path d="M9 3H3v18h6m4-14 5 5-5 5m-6-5h14" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  check: <path d="m5 12 4 4L19 6" />,
  shield: <><path d="m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7l8-4Z" /><path d="m8 12 3 3 5-5" /></>,
};
export function UiIcon({ name }: { name: keyof typeof paths }) {
  return <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{paths[name]}</svg>;
}
export function initials(name: string) {
  return name.trim().split(/\s+/u).slice(0, 2).map(word => word[0] ?? '').join('').toLocaleUpperCase('ru-RU');
}
