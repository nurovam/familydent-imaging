# Backend accounts and assignments implementation plan

> Исполнение: superpowers:executing-plans, без автоматического merge следующего PR.

Цель: PostgreSQL аккаунты + пароль/TOTP + server sessions + явно назначенные studies. Роли doctor, imaging_staff, platform_admin. Оператор один — FamilyDent; partner Clinic/Membership не создаёт права к Study. Медданные не доступны platform_admin по одной роли. Synthetic dev only.

- [x] Schema и Alembic: Clinic/User/Membership/Patient/Study/Assignment/AuthChallenge/AuthSession/AuthThrottle/AuditEvent. PostgreSQL, отдельная app роль; audit app-role append-only.
- [x] Test-first: password-only denied, TOTP enrollment/verify/replay/parallel redemption/attempts/expiry, account/IP throttle, CSRF, logout/idle/absolute expiry, deactivate user/membership, doctors isolation/search/pagination, duplicates/integrity, revoke assignment, audit no credentials and append-only.
- [x] Реализовать FastAPI auth/me + staff metadata/assign/revoke + admin account/clinic controls. Сырой opaque token только cookie; hash в DB. TOTP encrypted Fernet, password Argon2. No recovery by email, no public registration.
- [x] Подключить frontend login и server-backed studies с существующим CSS. Demo fixtures только отдельный явно marked demo path; без fail-open fallback.
- [x] Isolated local Compose PG, migrations, random local env generator и interactive admin bootstrap; локальный app-user не superuser. Никаких внешних migrations.
- [x] CI: реальные PG migrations/integration, lint/types, API contract, браузер login/TOTP/scope; отдельное ревью и исправления, PR report.

Временные параметры автора реализации: challenge5мин/5попыток; TOTP6digits/30сек/window±1 с replay counter; password throttle5/account/15мин,30/IP/15мин, TOTP5/account/15мин; session idle30мин/absolute8ч, отзыв и account.active на каждом request. Точные эксплуатационные значения ещё требуют приёмки перед пилотом.

Этот этап не переносит DICOM gateway из эксперимента в production service и не реализует импорт/ZIP/recovery. Studies сейчас — только metadata и назначения, state REGISTERED; выдача изображений появится после интеграции общей policy. Не объявлять готовность медицинского портала.

Результат: services/api/README.md; CI/PR проверяются после публикации. Рулинг: новый stage ограничен metadata policy, imaging experiment не интегрирован в auth-сервис; recovery и password change отложены до отдельной задачи.
