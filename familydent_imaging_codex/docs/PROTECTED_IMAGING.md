# Защищённый imaging — локальная проверка

Только synthetic development на Linux. Это первый сквозной сценарий; совместимость с клиническими экспортами Romexis и диагностическая пригодность не подтверждены. Реальные DICOM, NAS, SMTP и production не подключать.

## Запуск

Из корня, существующий infra/local/.env сохранять:

```sh
docker compose -f infra/local/compose.yaml --profile imaging up -d --wait db orthanc ohif viewer
cd services/api
uv sync --frozen
uv run python -m app.manage migrate
uv run python -m app.runtime
```

Отдельные терминалы: из services/api `uv run python -m app.worker`, из apps/web `npm run dev`. Основной портал http://127.0.0.1:5173; просмотрщик http://127.0.0.1:8091. Вход и TOTP прежние. Сервисы dev используют существующую БД и не сбрасывают аккаунты, MFA, сессии или назначения.

Linux host-network adapter нужен лишь для соединения контейнерного Nginx с API, запущенным на host loopback. Все listener привязаны к127.0.0.1: API8100, Orthanc8044, OHIF8092, viewer gateway8091. Orthanc REST без browser-auth доступен локальным процессам разработчика; это **не** допустимая production topology. Не публиковать порты. Production требует private network и API/worker внутри сети без host REST ports. OHIF получает снимки через /api/imaging/dicom-web, не напрямую от Orthanc; cookie передаётся same-host между локальными портами. Использовать именно127.0.0.1, не смешивать localhost. Доступ к медицинским данным каждый раз проверяет backend.

## Ручной сценарий

1. Для готовых metadata fixtures выполнить seed-studies по backend README. Или создать synthetic пациента с внутренним ID вида SYN-IMPORT-001 и новое исследование.
2. Из services/api: `uv run python -m app.synthetic_dicom --patient-id SYN-DEMO-001`. Заменить ID на точный внутренний ID выбранной synthetic записи. Получится игнорируемый infra/local/synthetic-upload.zip, восемь геометрических CT-срезов. UID случайный на каждый запуск; клинические файлы генератор не читает.
3. Сотрудник открывает исследование → «Импорт DICOM» → выбирает ZIP → «Загрузить на проверку». Worker переводит QUEUED → REVIEW либо FAILED с безопасным кодом.
4. Сверить выбранного пациента/исследование, UID и количество файлов. Подтвердить checkbox и «Подтвердить исследование». Только теперь study READY/job PUBLISHED.
5. Назначить врачу через существующий диалог. Врач открывает исследование → «Открыть просмотр» либо «Скачать DICOM». ZIP содержит только неизменённые оригиналы, без Romexis Viewer, DICOMDIR и дополнительных документов.
6. Отозвать назначение сотрудником: следующие metadata/frame/HEAD/Range/download запросы закрываются. Данные, уже полученные браузером или сохранённые врачом, отозвать невозможно.

## Контракт и защита

- POST /api/staff/studies/{id}/imports — raw body application/dicom или application/zip, origin+CSRF+MFA, роль imaging_staff, один активный импорт на REGISTERED study. Filename не сохраняется и не участвует в пути.
- GET .../{id}/imports — состояния/безопасный error_code/UID/count. Это staff-only, не отдельное право врача на job.
- POST .../{id}/imports/{job}/publish {confirmed:true} — точная связь job/study, REVIEW и повторная проверка REGISTERED. Worker не публикует самостоятельно.
- GET /api/doctor/studies/{id}/imaging — только READY+PUBLISHED и действующее явное назначение, membership, clinic, doctor и MFA session. Admin по роли снимков не видит.
- /api/imaging/dicom-web/... — только GET/HEAD whitelist конкретного Study/Series/SOP из опубликованного индекса. Global QIDO, patient-history, WADO-URI, STOW, BulkDataURI и произвольные URLs закрыты. Range здесь намеренно400; resumable поддерживается только для оригиналов.
- /api/doctor/studies/{id}/originals и /instances/{instance}/original — GET/HEAD, SHA256-проверка перед ответом, single-range206/416, ETag/If-Range, no-store. На каждом запросе и между64KiB chunks проверяются свежие права/сессия. При отзыве поток обрывается; audit result aborted. Первоначальная DB-транзакция не удерживается во время скачивания.
- PG job queue переживает перезапуск. Один local worker через advisory lock, отдельный child на job, wall60s/CPU45s/address space768MiB. Crash не создаёт READY; повтор QUEUED возможен без overwrite Orthanc, с byte-exact readback SHA256. Входные ZIP и неиндексированные crash leftovers остаются приватными; автоматического удаления медицинских файлов нет.
- Аудит: import queued/validated/failed/published, imaging open, dicom read, download started/finished плюс текущие auth/assignment события. Ни filenames, parser exception text, payload, credentials, cookie или OTP не логируются.

## Ограничения этапа

Part-10, CT Image Storage, uncompressed Explicit/Implicit VR Little Endian, один grayscale frame/instance. Upload32MiB, instance16MiB, максимум256 файлов, expanded64MiB, ratio100. ZIP с path traversal, absolute/Windows paths, symlink/special entries, encryption, повреждением, разными study UID или повтором SOP отвергается. PatientID должен точно совпасть с local_identifier; ФИО не используется для сопоставления. Это не полная DICOM conformance validation и не настройка объёма для реальных CBCT.

Локальный storage threshold256MiB — предохранитель dev, не атомарная многопользовательская квота. Failed/crash artifacts не очищаются автоматически; оператор пересоздаёт только специально disposable стенд. Production storage reservation, cleanup TTL временных артефактов, backpressure/concurrency, external scanner/process sandbox и measured limits — перед пилотом отдельным этапом. Нельзя запускать этот dev worker на реальных файлах.

## Проверки

Из корня перед тестами:

```sh
IMAGING_API_PORT=8101 docker compose -f infra/local/compose.yaml --profile test --profile imaging up -d --wait testdb orthanc ohif viewer
cd services/api
uv run pytest -q
uv run python browser_check.py
```

Команды последовательны: обе очищают только familydent_test, не familydent_dev. Browser создаёт временный каталог synthetic imports и удаляет только его. Не запускать dev worker с TEST_DATABASE_URL. После теста восстановить dev viewer upstream командой из корня:

```sh
docker compose -f infra/local/compose.yaml --profile imaging up -d viewer
```

Обязательный backend CI запускает реальные PostgreSQL/Orthanc/OHIF и тот же browser scenario; requirements с hashes, снимки только synthetic, retention7days. Старый spike остаётся отдельным regression job. Публикация образов/deployment выключены.

Проверено локально: 27 pytest, реальный browser workflow с OHIF canvas и8 frames, byte-exact ZIP, отзыв frame/Range и stream abort. Static: Ruff/mypy/OpenAPI; frontend lint/types/test/build, npm audit0, pip-audit0; 19 исходных design assets неизменны. Проверены synthetic screenshots import320/375/768/1440 и матрица кабинетов320–1920, горизонтального overflow нет. Системная сборка Node24.15 не поддерживает TS strip; использовать установленный Node24.18 из nvm, CI использует официальный Node24.
