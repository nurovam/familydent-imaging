# Правила разработки v1

Согласовано: врачебный v1, FamilyDent — единственный оператор. React/TypeScript/Vite, FastAPI, PostgreSQL/SQLAlchemy/Alembic, private Orthanc, self-hosted OHIF, общий Python worker, Docker Compose/Nginx. Пароль + TOTP. Пациентский портал, самостоятельные клиники, Romexis bundle и автоматическое удаление — позже.

## Git
Короткие feat/, fix/, docs/, chore/ ветки от main; один результат на PR. Владелец явно разрешает merge; squash merge, удаление ветки. Прямые записи, force-push и удаление main запрещены. Исправления проходят тот же процесс. Теги версий v0.1.0 и далее неизменяемы; v1.0.0 только после приёмки v1. Merge не разрешает deployment.

## Тестирование
Unit проверяют policy, состояния, сроки. Integration используют disposable PostgreSQL и Orthanc. Playwright проверяет MFA → импорт → назначение → просмотр → скачивание → отзыв. Обязательны отрицательные сценарии: чужой врач/study/UID/job, незавершённый MFA, отзыв с действующей сессией и Range, hostile archives, несовпадение пациента, checksum оригинала и отсутствие секретов в логах. Значимые дефекты получают regression test. Нет цели процента покрытия и тестов, дублирующих простую разметку. UI: изменённые экраны mobile/tablet/desktop, полная матрица handoff при переносе и перед v1.

## CI
На PR и main: quality, backend, imaging-e2e, итоговый ci-required. Реализованы quality/frontend/imaging-spike/backend/secrets и ci-required. Новые подсистемы получают реальные проверки вместе с кодом, без фиктивных pass. Итоговый job обязан зависеть от всех введённых обязательных jobs. При появлении зависимостей добавить lint/types/build, secret scan и dependency audit; новые high/critical findings блокируют merge без явного ограниченного по сроку исключения владельца.

GitHub-hosted runners — только synthetic fixtures. Нет production secrets, clinical network или runner в медицинской сети. Lockfiles, pinned actions SHA/images, read-only token; новые push отменяют старый CI PR. Flaky test исправляется, не маскируется retries. Отчёты/скриншоты synthetic хранятся 7 дней. Настройки защиты main требуют ci-required и актуальную ветку; запрет force/delete. Для solo-владельца явная команда на merge не заменяется недоступным self-approval GitHub.

## Выпуск
Пока приложения/Dockerfile нет, публикация образов выключена. После их появления successful main CI собирает private GHCR образы с SHA и digest, отдельный publish job получает только contents:read/packages:write. PR не публикует. Выпуск по завершённому сценарию, manual synthetic staging на isolated Compose, в production те же digest без rebuild. Тег фиксирует образы, commit и release notes. Обновление внутри собственной сети запускает оператор после отдельного разрешения владельца; GitHub не получает доступ к клинике.

Перед выпуском: успешный CI, проверка стенда, план отката, проверенный backup и явное разрешение. Деплои последовательны и не отменяются новым commit. Миграции обратно совместимы; приложение откатывается на прошлые образы, автоматический downgrade DB запрещён. Проверить smoke scenario и записать версию/исполнителя/время/результат. Мониторинг не содержит medical labels/payload. Проверка восстановления обязательна перед рабочим запуском.

## Готовность и границы
Этап завершён после демонстрации согласованного сценария, успешных обязательных тестов и приёмки без блокирующих дефектов. Новые функции идут в backlog, несвязанный рефакторинг — отдельным PR. Готовый дизайн сохраняется; security UX дополняется с согласованием. Реальные DICOM/PII/secrets не попадают в Git/CI. Старые документы Phase 0 — исторический полный roadmap; при расхождении по стеку/объёму v1 приоритет у этого документа и явных решений владельца.

Актуальное состояние: обязательные quality/frontend/imaging-spike/backend/secrets и ci-required. Backend использует PostgreSQL integration + browser TOTP/assignment tests, Gitleaks redacted history scan, pip-audit hashes. Production publishing по-прежнему выключен.
