# Frontend foundation — первый результат

React/Vite/TypeScript, список врача с поиском, фильтрами и деталями. Только synthetic fixtures. Исходный handoff не менялся. CSS и логотип перенесены; font files локальны через Fontsource/OFL. Точная версия шрифтов и pixel-accurate приёмка остаются открытыми.

Проверено: npm test (1 тест комбинации query/modality/status и empty), lint, typecheck, production build, npm audit (0 vulnerabilities), baseline repository checks, git diff --check. Headless Chromium desktop1440×900/mobile390×844 скриншоты просмотрены. Полная матрица9 и browser interaction e2e пока не выполнены; текущий тест проверяет чистую функцию поиска, не DOM.

Frontend CI добавлен к ci-required. Автоматического secret scanner пока нет; запрет credential files проверяет baseline script, это не полноценное обнаружение секретов. В следующем CI PR добавить полноценный scanner; до его появления требуется ручной просмотр diff. Backend/MFA/назначения/DICOM/download не реализованы; UI не является защитой доступа. Прямой URL показывает тот же demo screen.

Работа сделана поверх PR#1 без merge. Следующий технический этап — ранее согласованная ограниченная проверка Orthanc/gateway/OHIF на synthetic данных, затем auth и права. До готовой auth нельзя подключать клинический архив или публиковать UI как рабочий медицинский портал.
