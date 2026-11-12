# Protected imaging — локальная интеграция v1

Основание: TECH_SPEC.md, DEVELOPMENT.md и явная команда владельца продолжить после merge PR #4 (main 7a9035d). Область: только synthetic local development. Продолжение существующей ветки feat/protected-imaging; worktree не переносим во время прерванного прогона.

1. Проверить durable import queue, private storage, миграцию 0003 и worker. Приёмка: PatientID exact match, единый Study UID, уникальные SOP UID, лимиты архивов, ручной REVIEW → PUBLISHED; до подтверждения выдача закрыта.
2. Проверить реальную MFA/session/assignment policy для QIDO, metadata, instance/frame и оригиналов. Приёмка: чужой врач/admin/неизвестный UID/job закрыты, Range/HEAD и отзыв в действующей сессии, byte-exact DICOM/ZIP checksum.
3. Завершить сценарий в существующих диалогах без редизайна. Playwright: MFA → staff upload → worker → review → doctor OHIF canvas → ZIP → revoke frame/Range. Проверить mobile/tablet/desktop, внешние запросы отсутствуют.
4. Обновить pinned requirements, OpenAPI, обязательный backend CI с реальными Orthanc/OHIF; документацию запуска, ограничения и тестовые данные. Полная проверка и отдельное ревью ветки, PR; новый merge только по команде владельца.

Границы: Part-10 single-frame uncompressed grayscale CT; compressed/enhanced/multiframe и Romexis compatibility отдельным этапом. 32 MiB upload, 16 MiB/instance, 256 files, 64 MiB expanded, ratio ≤100. Эти dev limits не являются рабочими параметрами для CBCT. Viewer bundle выключен. Ресурсы только loopback; Linux-only host-network adapter для API на host. Public Orthanc, production deployment, реальные DICOM и автоматическое удаление запрещены.

Review focus: in-flight revoke; DB/session lifetime during streaming; worker crash/retry/UID collisions; archive metadata filtering; file/CPU/memory limits; browser error paths; no payload/credentials in logs/artifacts; preserving existing accounts/TOTP and dev DB.
