# FamilyDent Imaging

Врачебный v1: безопасная выдача исследований конкретным врачам. Разработка ведётся только на синтетических данных; production-инфраструктура не подключена.

Сейчас работают локальные PostgreSQL-аккаунты, пароль+TOTP, server-side сессии, регистрация метаданных и назначения/отзыв, scoped список врача и управление аккаунтами. В основной портал подключён локальный synthetic сценарий: DICOM/ZIP → worker → подтверждение → назначенный врач → OHIF/оригиналы → отзыв. Приём реальных исследований и production пока запрещены.

## Запуск и проверка

- [Backend, локальная БД, создание аккаунтов и тесты](services/api/README.md).
- [Frontend](apps/web/README.md): из apps/web выполнить npm ci и npm run dev, открыть http://127.0.0.1:5173. Backend нужен для входа; static UI-demo отдельно на /demo.
- [Защищённый локальный импорт и просмотр](familydent_imaging_codex/docs/PROTECTED_IMAGING.md).
- [Изолированный imaging spike](experiments/imaging/README.md): только синтетические геометрические CT, loopback8090.

## Правила и документы

- [Правила разработки врачебного v1](familydent_imaging_codex/docs/DEVELOPMENT.md).
- [Backend этап и критерии](familydent_imaging_codex/docs/BACKEND_AUTH_PLAN.md).
- [Исходное ТЗ полного MVP](familydent_imaging_codex/docs/TECH_SPEC.md).
- [Историческая архитектура и полный roadmap Phase0](familydent_imaging_codex/docs/ARCHITECTURE.md), [план](familydent_imaging_codex/docs/IMPLEMENTATION_PLAN.md).
- [Сопоставление дизайна](familydent_imaging_codex/docs/DESIGN_MAPPING.md), [открытые решения](familydent_imaging_codex/docs/DECISIONS_NEEDED.md), [Phase0 аудит](familydent_imaging_codex/docs/PHASE_0_AUDIT.md).
- [Неизменяемый handoff OpenDesign](Медицинский-портал-FamilyDent/DESIGN-HANDOFF.md).

Все исходные дизайн-файлы сохранены. Безопасность локального backend не является подтверждением юридической, диагностической или эксплуатационной готовности. Не хранить DICOM, данные пациентов, .env и credentials в Git/CI. Merge и рабочий deployment требуют отдельных явных команд владельца.
