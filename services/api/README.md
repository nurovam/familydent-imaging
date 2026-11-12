# Backend: accounts, MFA and assignments

Стадия локального врачебного v1. FastAPI, SQLAlchemy/Alembic, PostgreSQL. Реальные медицинские данные и production подключения запрещены. DICOM gateway из experiments/ не перенесён в этот сервис: текущие studies — метаданные в REGISTERED, не готовые к просмотру снимки.

## Запуск из корня репозитория

Требуются Python3.12+, uv, Node24 и Docker Compose.

```sh
python3 infra/local/init_env.py
docker compose -f infra/local/compose.yaml up -d --wait db
cd services/api
uv sync --frozen
uv run python -m app.manage migrate
uv run python -m app.manage bootstrap-admin
uv run python -m app.runtime
```

init_env.py создаёт случайные локальные ключи и пароли в infra/local/.env с правами0600, никогда не перезаписывает существующий файл и не печатает секреты. При повторном запуске пропустить его. Миграция запускается отдельно административной DB-ролью; API использует familydent_app без superuser/DDL прав. Веб-приложение никогда не мигрирует БД автоматически. Dev PG привязан к127.0.0.1:55432, API к127.0.0.1:8100.

В отдельном терминале из apps/web: `npm ci` и `npm run dev`. Открыть http://127.0.0.1:5173. Vite проксирует /api в backend. По умолчанию требуется настоящий вход; старые fixtures доступны только на /demo. Нет fallback к demo при сбое API.

Вместо bootstrap-admin можно **только на пустой локальной DB** выполнить `uv run python -m app.manage seed-demo`. Это создаёт admin/staff/doctor/other@example.test. Случайные начальные пароли записываются только в игнорируемый infra/local/.demo-credentials (0600), не в stdout. Не публиковать этот файл. При первом входе добавить показанный ключ в приложение-аутентификатор (TOTP6digits/30sec) и подтвердить кодом. Admin создаёт клиники и staff; staff создаёт проверенных врачей, регистрирует пациента по внутреннему ID, study и назначение. Admin не видит medical list по своей роли.

Не удалять .env при существующем dev volume: смена DB-паролей или TOTP_KEY не обновляет старую БД и делает старые TOTP недоступными. Это ещё не реализация secret rotation. TestDB отделена, tmpfs на127.0.0.1:55433; dev DB сохраняется в собственном Docker volume, без NAS/mount медицинских каталогов.

## Контракты

- POST /api/auth/password → HttpOnly challenge-cookie и enroll_totp/verify_totp; пароль сам по себе не даёт прав.
- POST /api/auth/totp/enroll → setup key/URI лишь для нового MFA после проверки пароля; существующий ключ повторно не выдаётся.
- POST /api/auth/totp → одноразовое потребление challenge, новая opaque session cookie и инвалидирование прежней сессии этого браузера.
- GET /api/auth/me → account/role и CSRF token; POST /api/auth/logout отзывает сессию.
- GET /api/doctor/studies?q=&limit=&offset= и /{id}: только active explicit assignment + active membership/clinic/doctor. Search/count scoped, неизвестный/чужой study дают одинаковый404.
- Staff: patient registration/точный поиск по local_identifier, study metadata registration, list, assign/list assignments/revoke. Не объединять по имени; email не идентификатор пациента.
- Admin: create clinic/accounts, disable account, revoke membership. Staff может создать doctor, но не staff/admin. Public registration и role selection при входе отсутствуют.

OpenAPI snapshot: packages/contracts/openapi.json. `uv run python export_openapi.py` обновляет, `--check` проверяет. Никаких реальных DB/секретов при экспорте.

## Безопасность и audit

Argon2id password hashes, Fernet encryption TOTP, keyed digests для cookie/challenge/rate-limit keys. Ключи отдельно от БД; API их не возвращает. TOTP pending секрет выдаётся только в enrollment response; не в URL/cookie/localStorage/log. Каждый TOTP проверяется с окном±1step и сохранением принятого счётчика под блокировкой User. Повтор кода и параллельный double redemption отвергаются. Общий порядок MFA/disable locks: User → challenge/session, совместимый с disable. User блокируется через NO KEY UPDATE, чтобы audit FK KEY SHARE не создавал цикл с session lock.

Предварительные параметры: challenge5мин/5ошибок, password5неудач/account/15мин,30password requests/IP/15мин, TOTP5неудач/account/15мин; successful authentication сбрасывает account failure counter. Session idle30мин, absolute8ч. Account.active проверяется на каждом запросе; disable отзывает sessions/challenges/assignments. Membership/assignment revoke немедленно меняет последующие scoped queries. Уже полученные данные вернуть невозможно.

Все mutations требуют точный Origin. После MFA дополнительно требуется X-CSRF-Token. Cookie HttpOnly/SameSite=strict, Secure по умолчанию. DEVELOPMENT=true разрешён только для loopback origin и снимает Secure ради локального HTTP; production config требует HTTPS. Origin, proxy trust и лимиты перед пилотом пересмотреть; X-Forwarded-For сейчас не доверяем, поэтому dev proxy разделяет один IP-limit.

Аудит транзакционный, timestamps UTC, actor/target identifiers/request_id/action/result, без ФИО, паролей, кодов и cookie. App DB-role может audit SELECT/INSERT, не UPDATE/DELETE/TRUNCATE/DDL. Изменения assignments содержат assignment/doctor/clinic/study IDs; account/membership changes — target IDs. Staff/doctor чтения study-list отражаются в audit. Migration role существует отдельно и не используется API.

## Проверки

```sh
# Из корня, только для disposable synthetic testdb:
docker compose -f infra/local/compose.yaml --profile test up -d --wait testdb
# Далее из services/api:
uv run pytest -q
uv run ruff check app tests browser_check.py export_openapi.py
uv run mypy app
uv run python export_openapi.py --check
uv run pip-audit --disable-pip --require-hashes -r requirements.txt
uv run playwright install --with-deps chromium
uv run python browser_check.py
```

**Не запускать pytest и browser_check.py параллельно:** оба очищают только familydent_test. Test fixture отказывается очищать другую DB; .env содержит отдельные TEST URLs. Dev DB и demo accounts тестами не затрагиваются.

17 PostgreSQL tests: MFA/replay/expiry/CSRF/IP/account limits, concurrent redeem/disable lock order, doctors isolation/revoke/membership/deactivate, schema integrity, audit/read/target identifiers, app-role permissions, migration downgrade-base/upgrade-head на disposable DB. Browser реально проходит password→TOTP→staff registration/assignment→doctor/other isolation→revoke→admin denied medical list. Скриншоты synthetic только в test-results/, не Git. Есть upstream Starlette TestClient deprecation warning про httpx; тесты проходят, это не suppressed error.

Dependencies pinned в uv.lock и requirements*.txt с hashes. Regenerate: `uv export --frozen --no-dev --format requirements-txt > requirements.txt`, `uv export --frozen --all-groups --format requirements-txt > requirements-test.txt`. CI ставит их с --require-hashes. Gitleaks сканирует Git history с --redact; отчёт не содержит исходных секретов.

## Открытые ограничения

Нет recovery/password change/MFA reset/rotation/операционного cleanup auth tables; до пилота нужен проверенный регламент. Аккаунт создаётся уполномоченным сотрудником после проверки врача; процедура пока организационная. Клиники — справочник одного оператора FamilyDent, не независимые tenants. UI staff/admin показывает первые страницы справочников; полноценная навигация больших staff списков и визуальная приёмка новых security forms ещё впереди. При первичной настройке QR строится локально в браузере из provisioning URI; ручной ключ доступен как fallback. При обычном входе QR и ключ не показываются. Нет DICOM import/ZIP/production streaming, READY transition или policy actions для выдачи изображений. При переносе imaging использовать отдельную action-aware READY policy, а не только текущую metadata policy. Этот этап не делает портал production-ready.

## Данные для ручной проверки

После `seed-demo` выполнить из services/api:

```sh
uv run python -m app.manage seed-studies
```

Команда разрешена только для loopback familydent_dev и существующих активных SYNTHETIC аккаунтов. Добавляет 8 пациентов SYN-DEMO-001…008 и 12 исследований с явными тестовыми подписями. Набор: doctor@example.test видит5 исследований; other@example.test —3; staff видит все12, в том числе2 неназначенных,1 заблокированное и1 с отозванным назначением. У одного пациента есть исследования разных врачей — история по пациенту не расширяет права.

Повторный запуск не создаёт дубли и не восстанавливает отозванные доступы, не меняет existing patients, статусы studies, пароли, TOTP или сессии. Коллизия внутреннего ID прекращает транзакцию без перезаписи. Это metadata REGISTERED/BLOCKED, **не DICOM-файлы**: реальный просмотр по-прежнему в отдельном synthetic imaging spike. Никаких migrations/удалений/сбросов для заполнения не требуется.

Актуально18 PostgreSQL tests, включая idempotent seed, разные doctor scopes и сохранность MFA/session/revocations.

Browser E2E декодирует QR в памяти (включая mobile390px), сверяет secret/issuer, входит кодом из QR и проверяет исчезновение QR после настройки и при повторном входе. Изображения enrollment QR не записываются в test artifacts; ошибки browser-check не печатают sensitive aria snapshots.
