# Frontend foundation

Node.js 24+, npm.

```sh
npm ci
npm run dev
```

Открыть http://127.0.0.1:5173. Экран списка врача, поиск/фильтры/детали на трёх синтетических fixtures. Это демонстрация, без auth, реальных DICOM и backend. Не вводить реальные данные. Все адреса SPA пока показывают этот единственный экран.

Проверки: npm test, npm run lint, npm run typecheck, npm run build, npm audit --audit-level=high.

CSS перенесён из исходного handoff без внешнего Google Fonts import; исходник не меняется. Golos Text/Roboto Serif self-hosted через Fontsource (лицензии OFL включены в npm-пакеты). Версии шрифтов пока не подтверждены владельцем как pixel baseline. Полный перенос экранов и визуальная приёмка ещё впереди.

Это первый PR основы UI; выбранный ранее ранний Orthanc/OHIF compatibility spike остаётся следующим отдельным заданием. Публикации и production deployment нет.

## Backend integration

Основной маршрут теперь использует настоящий API (локальный backend127.0.0.1:8100 через Vite proxy). Пароль/TOTP, staff metadata/назначения, admin accounts и server-scoped список врача. Запуск/локальные аккаунты: ../../services/api/README.md. Исходный fixture screen сохранён только на /demo, не fallback при недоступности backend. Для browser E2E отдельный Vite5174 проксирует тестовый backend8101; production endpoints не используются.
