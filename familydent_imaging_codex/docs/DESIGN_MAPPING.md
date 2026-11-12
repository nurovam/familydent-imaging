# FamilyDent Imaging — сопоставление дизайна и требований

Дата: 12.11.2026. Источник визуальных решений: ../../Медицинский-портал-FamilyDent/. Новый дизайн не создавался, экспорт не изменён. ТЗ приоритетно для безопасности; любые вынужденные UX-отклонения ниже подлежат проверке владельцем.

## 1. Инвентаризация и правила переноса

Handoff 25f996de-ff02-4e8a-9597-c7a2bd0c5b9d: DESIGN-HANDOFF.md, DESIGN-MANIFEST.json, DESIGN.md, brand-spec.md; index/login/doctor/study/upload/admin/patient.html; styles.css; app.js; assets/logo.svg, logo-family-dent.svg, logo-family-dent-diagnostics.svg; image.png; verification.json; critique.json. Все 17 sourceFiles manifest найдены (сам handoff и manifest дополняют набор). SKILL.md отсутствует, но handoff есть, поэтому отсутствие SKILL.md само по себе не блокирует работу. image.png проверен визуально: логотип Family diagnostic, не экранный baseline.

index.html помечен launcher-overview, не готовой production landing page. Экран-файл переносится отдельным маршрутом, не объединять всё в dashboard. Общие композиции: sidebar/topbar/breadcrumb, плотная таблица, right rail, pills, badges, dialog/toast, steps, формы, series rail, dark viewer canvas, patient download options. Пиксельное соответствие пока не подтверждено: visualCheck unavailable, responsive static-only. Локальные файлы Golos Text/Roboto Serif отсутствуют; styles.css:1 импортирует Google Fonts. До sensitive UI нужно self-host лицензированных версий без обращения к CDN.

## 2. Матрица «экран → компоненты → сценарий»

| Источник / будущий маршрут (предложение) | Компоненты | Сценарии ТЗ | Найденное / необходимое изменение |
|---|---|---|---|
| index.html → / (публичный вход отдельно от demo launcher) | бренд, заголовок, launch cards | §3C, §9.1 | Есть обзор всех пространств; нет явного безопасного входа «Получить исследование». Не делать launcher прямым доступом к private routes |
| login.html + app.js:115–121 → /doctor/login, /staff/login, /admin/login | auth story, email/code form, error | §2,5,9.4 | OTP 246810, пользователь выбирает роль; нет MFA. Сохранить композицию, заменить модель входа; роли выдаёт сервер, TOTP/passkey отдельный шаг |
| doctor.html + app.js:34–49 → /doctor/studies | sidebar, статистика, search, modality/status tabs, table, right rail, history dialog | §5,9.4 | Нет server scope/пагинации, история объединяется по имени. Показывать только явно assigned studies, history только в пределах прав и patient_id, без общей истории |
| study.html + app.js:86–107 → /doctor/studies/[id]/viewer и /patient-access/viewer | header, series rail, toolbar, canvas, slider, metadata, download/share dialog | §7,8,9.3 | Синтетический canvas без DICOM; share выдаёт token URL. OHIF требует feasibility; убрать выдачу пациентских ссылок врачом, скрыть Viewer bundle до лицензии |
| patient.html + app.js:109–113 → /patient-access/study | patient header, preview, metadata, downloads, expiry notice | §3C,4,9.2–3 | Доступен исходный fixture без claim, token в URL и localStorage. Нужны email→OTP→card→single-study session; no history; revoked/expired/blocked states |
| upload.html + app.js:124–147 → /staff/studies/new, /staff/imports/[id] | upload steps, dropzone, form, doctor/clinic selectors, review | §3A–B,4,9.5 | Только extension/size и local metadata. Нет local_identifier, identity/contact OTP, представителей, UID review/quarantine, карточки/отзыва. Развести регистрацию и import review |
| admin.html + app.js:150–181 → /admin/team, /admin/clinics, /staff/grants, /admin/audit | tabs, search, staff table, role/status controls, clinic cards, links, audit | §2,4,9.6,11 | 3 роли вместо 6, локальная смена ролей/журнал, временные ссылки. Заменить ссылки на адресные grants; разделить staff/platform/clinic permissions; нет incidents/retention |

## 3. Не покрытые handoff экраны и состояния

Для следующих сценариев нет утверждённого полного макета. Использовать существующие формы/панели как визуальные основы, но не выдавать предложенную композицию за утверждённую. Недостающие handoff-артефакты передать в исходный каталог в подпапку supplements/ с manifest и отдельными HTML/скриншотами; имя файла ниже — точный предлагаемый путь, не обнаруженный файл.

| Недостающий артефакт в supplements/ | Требуемые состояния | Приоритет / до какой работы |
|---|---|---|
| patient-access.html | email, neutral sent, OTP, resend cooldown, 5 attempts/expired, card input, generic claim failure, busy | P0 до patient UI Phase 1 |
| patient-access-unavailable.html | grant expired/revoked, session idle/absolute timeout, PENDING_IDENTITY, study not READY/blocked, offline | P0 до Phase 3 |
| mfa.html | enrollment, confirmation, challenge, failed/locked, lost-device assisted recovery | P0 до B2B/staff integration |
| staff-patient.html | local_identifier, distinct same-name records, identity method/status, contact verification, representative authority | P0 до Phase 3 |
| staff-card.html | single-study grant, controlled print, handover confirmation, failed print/reissue, revoke, old code invalid | P0 до Phase 3 |
| staff-import-review.html | progress, archive rejection, UID mismatch, quarantine/review/retry/blocked, second-person correction | P0 до Phase 5 |
| access-management.html | assignment/reassignment, revocation pending/success, doctor departure, wrong-patient incident | P0 до Phase 4/5 |
| downloads.html | preparing/ready/failed/expired, no permission after ready, cancel/resume, Viewer disabled | P1 до Phase 5 |
| admin-incidents-retention.html | incident creation/review, dry-run separated scopes, retention holds, deletion disabled | P1 до Phase 6 |
| clinic-members.html | clinic_admin bounded membership, no study access, invitation verified/expired/revoked | P1 до Phase 4 |

Все data screens: loading/empty/error/success/disabled, keyboard focus/validation, no-permission, server unavailable, mobile long names/identifiers и reduced motion. Текущие focus-visible и aria атрибуты — основа, не доказательство accessibility.

## 4. Зафиксированные визуальные токены

Канонический приоритет: реальные styles.css и проверенные макеты, затем brand-spec.md. Есть расхождение semantic colors: brand-spec success 53%/.13, error 58%/.18; CSS success 38%/.08, danger 46%/.16. Не усреднять; предложено сохранять CSS, подтверждение D02.

| Назначение | Точное значение CSS |
|---|---|
| bg / surface | oklch(97.8% .006 85) / oklch(100% 0 0) |
| fg / muted / border | oklch(23% 0 0) / oklch(49% .012 85) / oklch(89% .009 85) |
| accent / trust | oklch(78% .055 82) / oklch(36% .047 174) |
| success / danger | oklch(38% .08 160) / oklch(46% .16 25) |
| dark / dark-line / dark-muted | oklch(20% .006 165) / oklch(100% 0 0/.13) / oklch(76% .006 85) |
| type | Roboto Serif / Golos Text / ui-monospace; fallback как в CSS |
| radius / ease | --radius:18px; cubic-bezier(.23,1,.32,1); прочие радиусы сохранить по селекторам |

Breakpoints styles.css: max 1200/900/600 и min 1600; reduced-motion reduce. Handoff требует проверки 360×800,390×844,430×932,600×960,820×1180,1024×768,1366×768,1440×900,1920×1080. Сохранить fluid clamp, 8px rhythm, геометрию sidebar/table/right rail, локальные SVG. Спецификация требует русский UI. Копировать тексты только где они не противоречат безопасности.

## 5. Обязательные отклонения поведения без редизайна

1. token query links/share/email заменить общим публичным URL и очной карточкой ≥128 бит; врач не выдаёт доступ пациенту самостоятельно.
2. Код 246810 и выбор роли не переносить в auth; email OTP не MFA сотрудников.
3. localStorage state/audit/roles не переносить как механизм безопасности; fixtures держать в памяти и только для UI.
4. Историю по ФИО заменить patient_id + отдельный access scope; счётчики также scoped.
5. Удалить medical identifier из mailto/support и не переносить внешние fonts/telemetry.
6. Viewer bundle выключить, canvas оставить явно synthetic demo до OHIF; не выдавать pixel ruler за медицинские измерения.
7. Жёсткую дату max DOB=2026-11-01 и лимит 2ГБ в прототипе не считать политикой: дата должна быть актуальна, размер подтверждён нагрузкой/форматами.

## 6. Доказательства соответствия для Phase 1

Снять baseline локального handoff без внешнего сетевого трафика после согласования локальных шрифтов; экспорт не менять, подмена ресурсов возможна только в test harness. Затем скриншоты каждого существующего экрана на 9 размерах, сравнение геометрии/токенов/типографики; отдельно согласованные security UX отличия. Проверить viewport overflow, keyboard, focus traps/return, form labels, contrast и screen-reader semantics. Сейчас screenshot matrix не выполнена и pixel-accuracy не заявляется.
