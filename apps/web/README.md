# Frontend

React/TypeScript/Vite, Node24+. Из этого каталога:

```sh
npm ci
npm run dev
```

Открыть http://127.0.0.1:5173. Главный маршрут требует реального backend: [запуск PostgreSQL/API и локальных аккаунтов](../../services/api/README.md). Vite проксирует /api в127.0.0.1:8100. Login password→TOTP, staff metadata/назначения, admin accounts и server-scoped doctor list. При недоступном backend показывается ошибка, без fallback к fixtures.

Старый демонстрационный список с поиском/фильтрами/деталями на трёх fixtures сохранён на /demo. В нём нет auth и настоящих файлов; не использовать как medical portal.

Проверки: npm test, npm run lint, npm run typecheck, npm run build, npm audit --audit-level=high. Browser E2E запускается из services/api: отдельный frontend5174→test backend8101 и disposable PostgreSQL. Никаких production endpoints.

CSS и SVG из существующего handoff. Google Fonts import не перенесён, шрифты self-hosted через Fontsource/OFL. Исходный экспорт не меняется. Версии шрифтов и дополненные security UX формы требуют визуальной приёмки; pixel-accurate соответствие всех экранов не заявляется. Импорт/просмотр/скачивание DICOM в основной портал ещё не подключены.
