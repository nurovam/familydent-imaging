# FamilyDent Imaging — решения и риски

12.11.2026. Все решения ниже открыты; рекомендации не являются согласием владельца. Phase 0 не требует подключения инфраструктуры.

| ID / приоритет | Решение и владелец | Что нужно получить | Безопасное временное положение / блокируемый этап |
|---|---|---|---|
| D01 P0 | Владелец продукта + дизайнер: утверждён ли именно экспорт 25f996de… | Подтвердить каталог, ревизию/дата, дополнить supplements из DESIGN_MAPPING | Сохранить export неизменным; отсутствующие макеты не выдумывать; blocker полного Phase 1 |
| D02 P0 | Дизайнер: фактические шрифты и semantic tokens | Лицензированные локальные Golos Text/Roboto Serif, weight/variable versions, эталон screenshots; CSS vs brand-spec | Нет Google Fonts на sensitive UI; до решения нет заявления pixel-accuracy |
| D03 P0 | Владелец + архитектор: tenant/clinic semantics | FamilyDent как владелец; филиалы и внешние клиники, memberships врача в нескольких организациях | clinic membership не даёт права; deny by default; до schema Phase 2 |
| D04 P0 | Владелец + юрист + руководитель клиники: identity/representatives/recovery | Регламент проверки личности без копий документов, дети/согласия, нет документа, потеря карточки, смена email, срок проверки | PENDING_IDENTITY, no email-only recovery, no remote access без полномочий; до Phase 3 |
| D05 P0 | Security owner: параметры OTP/card/session/MFA | Cooldown, адрес/IP/device/global limits, absolute TTL, card validity/reprint, TOTP vs passkey и recovery сотрудников | OTP предварительно 6 цифр/5мин/5 попыток, idle30мин, card≥128бит, MFA всем privileged; точные значения утвердить до Phase 3/4 |
| D06 P0 | Юрист: email/метаданные в Германии | Заключение по трансграничной обработке, договоры/consents и SMTP logging/retention | live_smtp_enabled=false; dev mail sink; до внешнего SMTP |
| D07 P0 | Юрист + поставщик Romexis | Версия экспорта, SOP classes/transfer syntaxes, DICOMDIR, право commercial redistribution Viewer | viewer_bundle_enabled=false; оригинальный DICOM без Viewer; до bundling |
| D08 P0 | Медицинский руководитель + юрист | Обязательное хранение originals/portal copy/backup/audit, основания удаления/legal hold, право пациента на копию | irreversible_deletion_enabled=false; 30–90 дней не утверждено; dry-run; до retention production |
| D09 P0 | Security + эксплуатация | Семантика отзыва long stream и допустимое окно bytes in flight, fail-closed при DB failure, proxy buffering | Запрет новых/Range запросов после commit, chunk checks; нельзя отозвать ранее скачанные байты; до Phase 5 sign-off |
| D10 P1 | Эксплуатация | Подтверждённые local VM/network/NAS/VPS в Таджикистане, независимый backup, RPO/RTO, интернет upload | Только isolated dev Compose, без prod endpoints; до Phase 6 |
| D11 P1 | Клиника + инженер DICOM | 10–20 синтетических/надлежаще обезличенных примеров всех modalities, фактические размеры, Romexis import roundtrip | Не брать клинические DICOM; limit2ГБ и SLA не утверждены; до Phase 5/perf |
| D12 P1 | Владелец + staff lead | Кто назначает врача, second-person review ошибок, выделение staff/clinic_admin/platform_admin прав | Doctor не shares; platform_admin не читает всё; до Phase 3/4 |
| D13 P1 | Медицинский руководитель + licensing/security | OHIF preview vs diagnostic purpose, совместимость, требования измерений/браузеров | Не обещать diagnostic certification/MPR/мм; до пилота |
| D14 P1 | Security + privacy | Состав/retention audit/IP/UA, доступ, integrity storage и process инцидента | Append-only app role, без payload/секретов; до Phase 6 |
| D15 P1 | Архитектор | Точные версии Next.js/FastAPI/SQLAlchemy/Orthanc/OHIF и PostgreSQL queue lease/retry | Не устанавливать/не scaffold в Phase 0; pin и compatibility test при соответствующей фазе |

## Обнаруженные проблемы с доказательствами

| ID / серьёзность | Источник | Следствие и план |
|---|---|---|
| F01 Critical при переносе в prod | app.js:79–113 shareDialog/patient; DESIGN.md | token URL + browser storage, открытый fixture; заменить Phase 3, оставить только как эталон UI |
| F02 Critical при переносе | app.js:115–121 | fixed OTP, selectable roles, нет MFA/server checks; Phase 3/4 |
| F03 High | app.js:6,34–49 | localStorage и grouping history по name, нет назначения/tenant scope; Phase 2/4 |
| F04 High | styles.css:1 | Google Fonts внешний запрос с чувствительной страницы; self-host до переноса |
| F05 High | app.js:76 downloadDialog | mailto subject содержит study identifier; запретить medical support mailto |
| F06 High | app.js:124–147 | только extension/size, нет archive/UID validation и identity; карантин Phase 5 |
| F07 High | study.html, patient.html | Romexis bundle виден без license gate; выключить до D07 |
| F08 Medium | styles.css:3 vs brand-spec.md | разные success/danger, шрифты отсутствуют; D02 |
| F09 Medium | verification.json | visual unavailable, responsive static-only; не считать рендер проверенным |
| F10 Medium | workspace inventory | Нет Git/CI/package/lock/backend; нельзя запустить full app или подтвердить build/security |
| F11 High | ТЗ §8,11 | отзыв в середине stream не определён до конца; отдельный gateway race test и D09 |
| F12 Medium | app.js:129 | жёсткий max DOB 01.11.2026, неподтверждённый 2ГБ лимит; корректировать будущую форму и policy |

Серьёзность прототипа означает риск слепого переноса, не обнаруженную утечку из работающего сервиса. Коммерческая/юридическая/медицинская готовность не установлена.

## Что можно продолжить после проверки Phase 0

Phase 1a: перенос только существующей визуальной основы на синтетических fixtures после D01/D02, без backend/auth/DICOM. Новые security UX формы — после получения дополнений handoff. Юридические и инфраструктурные решения не мешают изолированной UI работе, но блокируют соответствующие интеграции и пилот. Следующая фаза начинается только по новой явной команде.
