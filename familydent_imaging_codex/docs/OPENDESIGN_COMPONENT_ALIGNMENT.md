# OpenDesign — выравнивание элементов интерфейса

2026-11-13. Запрос владельца: посмотреть элементы исходного OpenDesign и сделать текущий интерфейс похожим. Это уточнение уже выбранного дизайна, не новая визуальная концепция. Источники: неизменяемые DESIGN.md, brand-spec.md, doctor.html, upload.html, admin.html, login.html и styles.css в Медицинский-портал-FamilyDent/. Сняты реальные reference screenshots с локальными bundled fonts, без загрузки Google Fonts.

Наблюдение: предыдущая коррекция плотности убрала не только лишние формы, но и характерные элементы эталона — белые поверхности с18px скруглением/рамкой, pill-кнопки, золотой пункт навигации, аватары/контекст строк. Поэтому текущая реализация выглядела как упрощённый реестр, хотя палитра/шрифты совпадали.

Принятое решение по явному запросу владельца: перенести компоненты экспортированного образца в существующие кабинеты. Сохранить1360px ограничение ширины, реестр на первом экране и формы по требованию, принятые ранее. Полный возврат к исходному dashboard с ненастоящими метриками, историей пациента и несуществующими маршрутами не подходит существующей модели доступа. Перерисовка с другим брендом противоречит источнику истины.

Изменения: gold active sidebar с исходными outline icons, нижний account block, белые bordered study/team registers, serif headings, pills44px+, fields12px, аватары с инициалами, semantic status badges, search icon, native task dialog как единая поверхность. Импорт — dashed file picker и индикатор реальных этапов Загрузка/Проверка/Готово. Выбранное имя видно только локально в форме; payload, лимиты и endpoints прежние. Не имитируем drag-and-drop, если пользовательский сценарий его не реализует.

Файлы: Workspace.tsx, ImagingTasks.tsx, TaskDialog.tsx, workspace.css, новый UiIcon.tsx; browser_check.py только визуальная матрица/проверка file picker. API, MFA, authorization scopes, исходные19 design assets и frontend dependencies не меняются.

Проверка: frontend lint/types/build; реальный synthetic browser MFA/import/worker/review/OHIF/ZIP/revoke и role isolation, file picker selection/focus, dialogs/Escape/return focus/logout. Кабинеты320/360/375/390/414/430/600/768/820/1024/1366/1440/1920; picker320/375/414/768/1440. Скриншоты picker375, кабинетов320/414/768/1440 и admin dialog1920 визуально проверены после прогона. Тесты прошли: вся auth/imaging цепочка, file picker focus/selection и матрица ролей/диалогов. Секреты/QR и DICOM не сохранять в Git или screenshots.
