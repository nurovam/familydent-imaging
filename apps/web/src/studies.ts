export type Study = { id: string; name: string; modality: string; title: string; date: string; fresh: boolean };
export const studies: readonly Study[] = [
  { id: 'FD-DEMO-001', name: 'Тестовый пациент А', modality: 'CBCT', title: 'КЛКТ обеих челюстей', date: '12.11.2026', fresh: true },
  { id: 'FD-DEMO-002', name: 'Тестовый пациент Б', modality: 'OPG', title: 'Панорамный снимок', date: '11.11.2026', fresh: false },
  { id: 'FD-DEMO-003', name: 'Тестовый пациент В', modality: 'IO', title: 'Прицельный снимок', date: '10.11.2026', fresh: true },
];
export function filterStudies(items: readonly Study[], query: string, modality: string, status: string): Study[] {
  const needle = query.trim().toLocaleLowerCase('ru');
  return items.filter(s => `${s.name} ${s.id}`.toLocaleLowerCase('ru').includes(needle)
    && (modality === 'all' || s.modality === modality)
    && (status === 'all' || (status === 'new' ? s.fresh : !s.fresh)));
}
