# FamilyDent Imaging — правила корня workspace

Обязательно прочитать и соблюдать familydent_imaging_codex/AGENTS.md, familydent_imaging_codex/docs/TECH_SPEC.md и familydent_imaging_codex/CODEX_FIRST_TASK.md. Их требования безопасности распространяются на весь монорепозиторий, включая дизайн-экспорт.

Дизайн-источник: Медицинский-портал-FamilyDent/; сохранять экспорт как эталон, не переносить его локальную модель доступа в production. План: familydent_imaging_codex/docs/IMPLEMENTATION_PLAN.md. Выполнять только явно назначенную фазу. Никаких production-сервисов или реальных медицинских данных без отдельной явной команды; данные пациентов/секреты/DICOM/ZIP не коммитить.

Для вопросов о библиотеках/API/CLI пользоваться Context7: сначала npx ctx7@latest library с полным вопросом, затем docs по выбранному ID; не более 3 команд на вопрос, без секретов. Context7 запускать вне sandbox. При quota сообщить пользователю о npx ctx7@latest login или CONTEXT7_API_KEY. Для общего аудита/refactoring без library-specific вопросов Context7 не нужен.
