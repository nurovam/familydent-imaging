# FamilyDent Imaging — подробный план реализации

> Для исполнителя: применять superpowers:subagent-driven-development или superpowers:executing-plans после явного назначения новой фазы. Чекбоксы ниже — будущая работа, не выполненная реализация.

**Цель:** безопасный обмен исследованиями с адресным доступом к одному study, с сохранением OpenDesign.
**Архитектура:** модульный FastAPI API и общий policy, отдельный worker, PostgreSQL, приватный Orthanc через DICOM gateway; React/Next.js UI и локальный OHIF.
**Стек:** TypeScript/React/Next.js, Python/FastAPI/Pydantic/SQLAlchemy/Alembic, PostgreSQL, Orthanc/DICOMweb/OHIF; версии закрепляются позже.
**Спецификация:** TECH_SPEC.md v1.1, ARCHITECTURE.md, DESIGN_MAPPING.md, DECISIONS_NEEDED.md. Документ — предложение, требующее проверки; следующий этап автоматически не начинается.

## Общие ограничения

- Patient access strictly per study_id, не по общей истории; email OTP плюс лично выданная карточка >=128 бит.
- Email не уникальный ключ пациента; не объединять по ФИО/email. Представительство проверяется отдельно.
- MFA для doctor/staff/admin; membership не назначение; clinic_admin/platform_admin не получают автоматического medical access.
- Каждый API/DICOMweb/download/HEAD/Range проверяет серверную policy; отзыв инвалидирует активные sessions.
- Только synthetic/надлежаще обезличенные данные; никогда real DICOM/PII в dev/CI/Git.
- Нет prod подключения/внешних миграций/удаления; live_smtp_enabled=false, viewer_bundle_enabled=false, irreversible_deletion_enabled=false.
- Нет CDN/foreign telemetry; все медицинские production данные и backup в Таджикистане. SMTP в Германии требует D06.
- Сохранять экспорт неизменным и visual system; отсутствующие макеты — вопросы, не приглашение придумать дизайн.

## Review focus — сквозные пограничные сценарии

1. Один email у нескольких пациентов и похожие имена: код A не открывает B; задача P3b.
2. Отзыв после создания ZIP/во время stream/перед Range: deny, прекращение новых chunks, job не даёт обход; P5c.
3. Смена контакта, представитель, потеря карточки: старые proofs/sessions не работают, email не восстанавливает права; P3c.
4. Увольнение/смена клиники и guessed UID/metadata: не выдавать данные или counts коллеги; P4b/P5b.
5. Crash worker между Orthanc и commit, hostile archive: no READY до review, idempotent retry и bounded resource use; P5a.

## Правило исполнения каждого PR

- [ ] Прочитать спецификацию и актуальные решения; остановиться на блокирующем решении.
- [ ] Для поведения сначала создать перечисленные negative/positive tests и подтвердить ожидаемый fail, затем минимальную реализацию.
- [ ] Выполнить тесты PR, static checks/build при наличии приложения, проверить diff на secrets/PII и изменённые UX.
- [ ] Обновить docs/контракты/миграции по необходимости; приложить результаты и ограничения; отдельный commit и review.

Ни одна команда тестов ниже сейчас не доступна как проектный runner: это точные будущие цели после создания соответствующего стека. В Phase 0 зависимости не ставились. Проверки документации и исходного прототипа отдельно в PHASE_0_AUDIT.md.

## Phase 0 — текущий аудит

Артефакты: ARCHITECTURE, DESIGN_MAPPING, DECISIONS_NEEDED, IMPLEMENTATION_PLAN, PHASE_0_AUDIT. Source inventory и SHA256 handoff фиксируются в отчёте. Git root предлагается в workspace, закрытый origin в аккаунте владельца; экспорт и входное ТЗ сохраняются.
Критерий: все 7 экранов сопоставлены, gaps/безопасные defaults отмечены, никакой реализации/инфраструктуры. Приёмка плана владельцем остаётся отдельным шагом.

## Phase 1 — UI Foundation (только после новой команды)

### P1a / PR01: визуальная основа и существующие экраны

Зависимости D01/D02. Создать apps/web/package.json и lockfile, src/styles/tokens.css, src/components/{AppShell,StudyTable,AuthPanel,UploadSteps,StudyViewerShell}, src/app с отдельными маршрутами, public/fonts и утверждёнными SVG; tests/e2e/design.spec.ts. Frontend fixtures в src/fixtures, из памяти; handoff JS с auth/localStorage не переносить. Launcher сохранить в изолированном demo route, public route по утверждённому сценарию.
Интерфейс: StudySummary(id, synthetic patient display, modality, state); UI data adapter возвращает только fixtures, не строит fake security. Точные DTO от API с Phase 2 заменят adapter.
- [ ] Перенести точные CSS tokens/fonts и композиции всех 7 экранов; не добавлять backend.
- [ ] Проверить routes, tabs/search, empty/errors на fixtures; demo viewer явно недиагностический.
- [ ] Снять reference/actual screenshot matrix на 9 viewports, выполнить keyboard/overflow/focus проверки и зафиксировать согласованные отличия.
Приёмка: нет внешних font/analytics запросов, реальные medical values не используются; Chromium визуальная QA. Команды после setup: npm --prefix apps/web ci; npm --prefix apps/web run lint; npm --prefix apps/web run typecheck; npm --prefix apps/web run build; npm --prefix apps/web run test:e2e -- design.spec.ts. В packages scripts закрепить именно эти имена.

### P1b / PR02: согласованные security UX состояния

Зависимость PR01 и supplements из DESIGN_MAPPING. Создать patient-access steps, MFA states, staff identity/card/quarantine/grant states в отдельных routes/components, tests/e2e/access-ui.spec.ts. Все действия mocked, без выдачи session/секретов.
- [ ] Реализовать только полученные/согласованные дополнения дизайна.
- [ ] Проверить generic errors без enumeration, expiry/revoked/disabled Viewer и no patient history.
Приёмка: сценарии §9 покрыты UI fixtures, доступность и mobile; новые UI решения отдельно утверждены. Те же lint/typecheck/build + access-ui.spec.ts. Phase 1a можно принять отдельно, Phase 1 целиком без supplements не считается завершённой.

## Phase 2 — Backend foundation

### P2a / PR03: схема, миграции и API DTO

Зависимость D03/D12; PR01 для согласования интерфейсов. Создать services/api/pyproject.toml+lock, app/models/, alembic/, packages/contracts/openapi.json, tests/integration/test_schema.py, infra/local/compose.yaml с isolated PostgreSQL.
Производит UUID Patient/Contact/Identity/Study/Recipient/Representation/Grant/Credential/Session/Clinic/Doctor/Membership/Assignment, jobs/outbox/audit/retention/incident из ARCHITECTURE; OpenAPI DTO/error envelope. Synthetic seed отдельной явной командой.
- [ ] Проверить composite FK tenant mismatch, duplicate local_identifier, shared email allowed, invalid dates/actions denied.
- [ ] Реализовать миграцию; upgrade на пустой disposable DB и upgrade предыдущей схемы, rollback только disposable DB.
Приёмка: schema constraints действуют, нет внешних endpoints/секретов. Команда будущего runner: pytest tests/integration/test_schema.py -q; alembic upgrade head только локально.

### P2b / PR04: policy и audit

Создать app/policy.py, auth/context.py, audit/service.py, contracts DTO; tests/security/test_policy.py и test_audit.py. Интерфейсы: AccessContext(actor_id,role,tenant_id,session_id,mfa_verified); authorize_study(context,study_id,action)->AuthorizedStudy; audit(event)->persisted event в той же transaction. Всё deny-by-default.
- [ ] Тестировать роли без medical grant, cross-tenant, revoked assignment, missing MFA, grant scope/actions/expiry.
- [ ] Проверить app-role не UPDATE/DELETE audit, rollback mutation не оставляет ложный success event, секреты redacted.
Приёмка: policy применяется через единую dependency всех medical routers; pytest tests/security/test_policy.py tests/security/test_audit.py -q + static typing/lint. Публичных DICOM ещё нет.

## Phase 3 — Patient access и staff выдача

### P3a / PR05: регистрация/identity/contact/карточка

D04/D05, PR04. Создать patients/service.py, grants/service.py, grants/cards.py, staff routers, tests/security/test_card_issue.py. Вход: patient_id/local_identifier, verified identity/contact/representation, study_id; результат grant_id и одноразово выводимый card secret, не повторно читаемый сервером. HMAC key versions, print/no-store, QR только public URL.
- [ ] Проверить PENDING_IDENTITY, contact unverified, wrong representative → issue denied; >=128-bit CSPRNG, hash only; no secret в logs/URL/audit.
- [ ] Подтверждение handed-over отдельным действием, не считать browser print доказательством выдачи.
Приёмка pytest tests/security/test_card_issue.py -q и staff UI synthetic e2e. Нет live mail.

### P3b / PR06: OTP → claim → single-study session

Создать auth/otp.py, grants/claim.py, auth/sessions.py, patient router; tests/security/test_patient_claim.py, tests/e2e/patient-access.spec.ts. Интерфейсы request_otp(email,purpose)->generic receipt; verify_otp(challenge_id,otp)->short-lived email proof; claim(email_proof,card_secret)->opaque cookie session одного grant/study.
- [ ] Атомарное одноразовое потребление, TTL5мин/5 attempts, resend инвалидирует старый challenge по утверждённой политике, rate-limit общий для workers.
- [ ] Email двух пациентов/нескольких studies: credential A не даёт B; proof и card связаны с recipient contact version, имя ничего не объединяет.
- [ ] Verify повторно/параллельно, expired/wrong/unknown дают нейтральный безопасный ответ; cookie rotation, CSRF/no-store/no localStorage.
Приёмка pytest tests/security/test_patient_claim.py -q + patient-access.spec.ts; приложение выдаёт только metadata fixture до imaging.

### P3c / PR07: отзыв, особые случаи и исправления

Создать grants/revocation.py, patients/recovery.py, incidents/service.py; tests/security/test_recovery_revocation.py. Интерфейс revoke_grant(grant_id,actor,reason)->revocation version в transaction; blocks sessions/credentials/jobs и audit. Reissue требует новую identity/representation проверку.
- [ ] Потеря карточки/смена email, ребёнок/родственник без authority, contact version changes, old email proofs denied.
- [ ] Ошибочная привязка BLOCKED немедленно, second-person correction, incident/audit неизменны.
Приёмка pytest tests/security/test_recovery_revocation.py -q + recovery e2e. Отзыв DICOM stream проверяется позже PR12.

## Phase 4 — B2B

### P4a / PR08: персональные учётные записи и MFA

D05/D12, PR04; app/auth/mfa.py, accounts.py, clinic membership/admin routers; tests/security/test_mfa.py. Серверные роли, verified invitation, TOTP/passkey по решению D05, privileged session с mfa_verified timestamp; recovery не по email-only.
- [ ] Login/challenge/replay/lockout/expired invitation, CSRF/session fixation, enrollment/recovery audit; clinic_admin не может повысить себя до platform_admin.
Приёмка pytest tests/security/test_mfa.py -q и B2B auth e2e.

### P4b / PR09: назначения и scoped поиск

PR08/PR04; studies/assignments.py, doctor/studies routes; tests/security/test_doctor_scope.py. Produces scoped paginated StudySummary[] из активных assignment+membership; same policy для details/counts/history/export.
- [ ] Doctor A/B в одной/разных клиниках, guessed id, invalid clinic parameter, revoked membership/увольнение, cross-tenant и shared-name records → нет утечки.
Приёмка pytest tests/security/test_doctor_scope.py -q + doctor e2e; просмотр только назначенного.

## Phase 5 — Imaging

### P5a / PR10: карантин, worker, Orthanc import

D07(format)/D11/D15, PR04. Создать imaging/imports.py, validators.py, reconcile.py, worker/import_job.py, infra/local Orthanc config, tests/integration/test_import.py; собственные synthetic fixtures с provenance. API upload->job_id; только staff; controlled import->READY после review.
- [ ] Тест zip-slip/bomb/symlink/nested archive, MIME mismatch, oversized aggregate/ratio/file count/CPU, corrupt DICOM, UID mismatch/duplicate; no publication.
- [ ] Job idempotency/lease expiry/retry, crash до/после Orthanc, no READY частично, cleanup изолированных временных файлов.
Приёмка pytest tests/integration/test_import.py -q; Orthanc не публичен, все лимиты явно заданы и проверены; реальные данные не нужны.

### P5b / PR11: DICOM gateway и OHIF synthetic spike

PR10/PR09/PR06. Создать imaging/gateway.py, uid_index.py, infra/ohif/, tests/security/test_dicomweb.py, tests/e2e/viewer.spec.ts. Вход authorized study + UID hierarchy; выход QIDO/WADO/metadata/bulkdata с gateway URLs. OHIF показывает synthetic fixtures; проверить перенос дизайна вокруг реального viewer, не писать renderer.
- [ ] Guessed series/instance, query filters/global QIDO, direct Orthanc URL, SSRF/unsafe BulkDataURI/STOW пациента → deny.
- [ ] Compatibility matrix SOP/transfer syntax/browser/series/slices, доступность toolbar и права по каждому request; unsupported format честно сообщается.
Приёмка pytest tests/security/test_dicomweb.py -q + viewer e2e; diagnostic suitability не заявляется.

### P5c / PR12: оригинальный ZIP, поток, отзыв и Range

D09/D07 license gate, PR11/PR07. Создать downloads/service.py, streaming.py, worker/download_job.py; tests/security/test_download_revocation.py и tests/integration/test_export.py. create_download(context,study)->owned job; poll/fetch только при актуальном праве; bytes исходного DICOM сохраняются по checksum; Viewer flag false.
- [ ] Revocation before headers/midstream/после READY, new HEAD/Range/resume, concurrent grant revoke, DB outage fail closed; проверять отсутствие новых разрешённых chunks после version invalidation.
- [ ] Correct 206/416, malformed/multi/suffix ranges, wrong job owner, archive TTL, no public static URL, bounded memory/disk.
- [ ] Synthetic ZIP roundtrip Romexis с подтверждённой версией; checksums originals, DICOMDIR если нужен; без лицензии bundle недоступен.
Приёмка pytest tests/security/test_download_revocation.py tests/integration/test_export.py -q; измерение revocation latency/transport buffer и согласование D09, без придуманного SLA.

## Phase 6 — Operations (всё ещё не production)

### P6a / PR13: outbox уведомления и test mail

D06 нужен до live SMTP, PR07/PR10; notifications/templates.py, worker/outbox.py, tests/security/test_notifications.py. Only neutral subject/body/general portal URL, no PII/study id/card/access URL/attachments. Dev sink, bounded retry/dedup, email/contact version проверяется перед отправкой.
- [ ] Snapshot содержимого, headers/log redaction, retry duplicate, cancelled grant/contact change, unknown email enumeration.
Приёмка pytest tests/security/test_notifications.py -q; live_smtp_enabled=false сохраняется.

### P6b / PR14: backup/restore, monitoring, retention dry-run, runbooks

D08/D10/D14; infra/local/, docs/runbooks/{backup,restore,incident,revocation,identity,retention}.md, tests/integration/test_retention.py. NAS integration только на отдельном явно разрешённом тестовом стенде, не на production NAS по умолчанию.
- [ ] Dry-run раздельно original/distribution/ZIP/audit/backup с legal holds; irreversible deletion disabled.
- [ ] Restore isolated encrypted synthetic backup, ransomware recovery сценарий, audit access separation; мониторинг без medical labels/payload.
Приёмка restore proof + pytest tests/integration/test_retention.py -q; RPO/RTO измерены и утверждены, не выдуманы. Production deployment — новое задание.

## Phase 7 — Hardening и решение о пилоте

### P7a / PR15: итоговая security/regulatory проверка

Все этапы выше, D04–D14, утверждённые threat model и data-flow inventory. tests/e2e/full-workflows.spec.ts + полная security suite; pentest, dependency/license/SBOM, perf на фактических synthetic/anonymized объёмах, backup evidence и operational training.
- [ ] Выполнить все 14 сценариев §12 и негативные ветви; конкретные failure evidence и remediation.
- [ ] Закрыть юридические/Viewer/diagnostic/SMTP/retention решения; отдельное одобрение ограниченного пилота владельцем. Наличие тестов не заменяет это одобрение.
Приёмка: отчёт, остаточные риски/ответственные, pilot rollback; без внешнего deployment в рамках текущей задачи.

## Покрытие требований TECH_SPEC.md

| Раздел | PR |
|---|---|
| §0,9,13 дизайн/порядок | Phase 0, PR01–02, gate каждого этапа |
| §1 MVP boundaries | все этапы; никаких payments/history/autosync |
| §2 роли/tenant | PR03–04,08–09 |
| §3 пациент/регистрация | PR05–07,10–12 |
| §4 представители/ошибки/recovery | PR05,07 |
| §5 B2B | PR08–09 |
| §6 модель | PR03–04,05–07 |
| §7 API | PR03–04 и контракты каждого следующего PR |
| §8 DICOM/export | PR10–12 |
| §10 инфраструктура | PR14 и отдельно разрешённое deployment |
| §11 audit/threats/retention | PR04,07,12–15 |
| §12 тесты 1–14 | 1:05/10; 2–3:06/12; 4:07/12; 5:06; 6–7:07; 8:09/11; 9:07; 10:12; 11:10; 12:13; 13:01/04/11/15; 14:04/15 |
| §14 нерешённые вопросы | DECISIONS_NEEDED, gates выше |

## Точное следующее задание

«Выполни только Phase 1a / PR01 после подтверждения D01/D02: создай frontend foundation из существующего OpenDesign, с отдельными маршрутами и синтетическими fixtures; локальные шрифты, токены/композиции без редизайна, screenshots 9 viewports и accessibility checks. Не подключай backend/SMTP/Orthanc/NAS, не реализуй authentication и не переходи в Phase 2. Отсутствующие security UX макеты вынеси в отдельный PR02 после согласования». Это предложение следующего задания, не текущая команда на реализацию.
