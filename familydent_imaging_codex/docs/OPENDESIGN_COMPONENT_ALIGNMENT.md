# OpenDesign — выравнивание элементов интерфейса

2026-11-13. Запрос владельца: посмотреть элементы исходного OpenDesign и сделать текущий интерфейс похожим. Это уточнение уже выбранного дизайна, не новая визуальная концепция. Источники: неизменяемые DESIGN.md, brand-spec.md, doctor.html, upload.html, admin.html, login.html и styles.css в Медицинский-портал-FamilyDent/. Сняты реальные reference screenshots с локальными bundled fonts, без загрузки Google Fonts.

Наблюдение: предыдущая коррекция плотности убрала не только лишние формы, но и характерные элементы эталона — белые поверхности с18px скруглением/рамкой, pill-кнопки, золотой пункт навигации, аватары/контекст строк. Поэтому текущая реализация выглядела как упрощённый реестр, хотя палитра/шрифты совпадали.

Принятое решение по явному запросу владельца: перенести компоненты экспортированного образца в существующие кабинеты. Сохранить1360px ограничение ширины, реестр на первом экране и формы по требованию, принятые ранее. Полный возврат к исходному dashboard с ненастоящими метриками, историей пациента и несуществующими маршрутами не подходит существующей модели доступа. Перерисовка с другим брендом противоречит источнику истины.

Изменения: gold active sidebar с исходными outline icons, нижний account block, белые bordered study/team registers, serif headings, pills44px+, fields12px, аватары с инициалами, semantic status badges, search icon, native task dialog как единая поверхность. Импорт — dashed file picker и индикатор реальных этапов Загрузка/Проверка/Готово. Выбранное имя видно только локально в форме; payload, лимиты и endpoints прежние. Не имитируем drag-and-drop, если пользовательский сценарий его не реализует.

Файлы: Workspace.tsx, ImagingTasks.tsx, TaskDialog.tsx, workspace.css, новый UiIcon.tsx; browser_check.py только визуальная матрица/проверка file picker. API, MFA, authorization scopes, исходные19 design assets и frontend dependencies не меняются.

Проверка: frontend lint/types/build; реальный synthetic browser MFA/import/worker/review/OHIF/ZIP/revoke и role isolation, file picker selection/focus, dialogs/Escape/return focus/logout. Кабинеты320/360/375/390/414/430/600/768/820/1024/1366/1440/1920; picker320/375/414/768/1440. Скриншоты picker375, кабинетов320/414/768/1440 и admin dialog1920 визуально проверены после прогона. Тесты прошли: вся auth/imaging цепочка, file picker focus/selection и матрица ролей/диалогов. Секреты/QR и DICOM не сохранять в Git или screenshots.

## Уточнение по изображению владельца

Владелец указал конкретную правую колонку: тёмная карточка последнего поступления с рисунком челюсти и кнопкой, ниже белая timeline «Последние события». Предыдущая коррекция одних controls не закрывала запрос. Добавить эти блоки doctor/staff рядом с реестром, на узких экранах ниже него. Иллюстрация из исходного app.js — явно подписанная схема, не реальный thumbnail. Карточка использует реальное последнее разрешённое исследование; события — минимальная проекция реального audit с той же Study policy. Никаких выдуманных пациентов/срезов/пациентских ссылок, других врачей или общего audit admin. Admin карточки медданных не получает. Без новых зависимостей и миграций.

Реализовано: StudyContext.tsx, DentalSketch.tsx (рисунок из неизменённого app.js), cabinet grid/rail styles, GET /api/workspace/overview с typed response и doctor_scope. Подтверждено29 PostgreSQL tests, включая overview access/revoke/blocked/admin/other-doctor; full browser card open→detail и real event, отсутствие карточки доступа после revoke,13-width matrix, no external requests. Скриншоты context-rail320/375/414/768/1440 сохраняются только в ignored test-results; desktop1440 и mobile375 визуально сравнены с присланным изображением. Ни миграций, ни live patient link событий не добавляли.

Ревью выявило крайний случай staff latest card за пределами25 строк реестра, когда первые25 исследований заблокированы: диалог раньше искал метаданные только в текущей странице. Regression browser воспроизвёл отказ. Исправление: карточка передаёт своё разрешённое StudySummary в existing staff dialog, сохраняя server-authorized endpoints. Добавлен сценарий с25 более новыми synthetic BLOCKED study, открытием старого latest study и его import dialog; данные создаются/удаляются только внутри disposable testdb. Остальных Critical/Important замечаний reviewer не отметил.

Regression RED→GREEN подтверждён повторным полным browser прогоном; обычный latest card, карточка вне первой страницы, import dialog, active-session revoke и responsive matrix проходят.

## Исправление выбора исследования в контекстной карточке

Воспроизведён дефект: после открытия «Тест02» детали показывали02, но StudyContext независимо использовал overview.latest и продолжал показывать01. Карточка теперь получает текущий выбор (у врача после успешной server detail проверки, у сотрудника из выбранной metadata записи). Заголовок меняется на «Выбранное исследование», выбранная строка получает aria-current и спокойный фон. Закрытие деталей/диалога сохраняет выбор; явное обновление реестра сбрасывает его к последнему поступлению. Данные latest API, права и методы скачивания не изменяются.

Regression context_selection_check.py воспроизвёл исходное расхождение RED, после исправления проходит для doctor и imaging_staff: выбор02, имя пациента02, правильный study ID в действии карточки, закрытие и сброс по Refresh. Он запускает реальный React с полностью перехваченными synthetic API responses, не обращается к БД и не заменяет real MFA/scope browser scenario. Добавлен в обязательный backend CI.
