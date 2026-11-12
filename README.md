# FamilyDent Imaging

Phase 0: аудит репозитория и существующего OpenDesign. Функциональность платформы пока не реализована.

- [Исходные правила](familydent_imaging_codex/AGENTS.md)
- [Техническое задание](familydent_imaging_codex/docs/TECH_SPEC.md)
- [План реализации](familydent_imaging_codex/docs/IMPLEMENTATION_PLAN.md)
- [Архитектура](familydent_imaging_codex/docs/ARCHITECTURE.md)
- [Сопоставление дизайна](familydent_imaging_codex/docs/DESIGN_MAPPING.md)
- [Открытые решения](familydent_imaging_codex/docs/DECISIONS_NEEDED.md)
- [Аудит Phase 0](familydent_imaging_codex/docs/PHASE_0_AUDIT.md)
- [Handoff OpenDesign](Медицинский-портал-FamilyDent/DESIGN-HANDOFF.md)

Экспорт содержит синтетический UI-прототип, не безопасную медицинскую систему. В нём нет backend/MFA/серверных прав/DICOM-декодера. Не вводить реальные данные и не публиковать его как работающий портал. styles.css обращается к Google Fonts; перед визуальной проверкой и переносом нужны согласованные локальные шрифты.

Нет установленного приложения/команд сборки: package/lockfiles и сервисы появятся только по отдельному заданию следующей фазы. Production-инфраструктура не подключалась. Не хранить DICOM, персональные данные или секреты в Git.
