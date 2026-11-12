# Synthetic imaging compatibility spike

**Только изолированная техническая проверка. Не clinical archive и не production auth.**

Стенд доказал работу Orthanc 25.11.0 → FastAPI gateway → OHIF 3.11.0 на геометрических CT fixtures. Это не подтверждение совместимости Romexis, JPEG2000, CBCT multi-frame/MPR, других modalities или диагностической пригодности. Это не новый дизайн: отдельный технический OHIF стенд без переноса в UI портала.

## Запуск

Требуются Docker Compose и Python3.12+. В этом каталоге:

```sh
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-test.txt
docker compose up -d --build
.venv/bin/python wait_ready.py
docker compose run --rm seed
```

Открыть http://127.0.0.1:8090/demo и нажать Open assigned synthetic study. Seed ждёт готовности Orthanc до 60 попыток. Сессия a разрешает только 2.25.20261112001. `/demo/open?actor=b` создаёт сессию без назначения — metadata/кадры запрещены. Эти endpoints намеренно доступны любому локальному пользователю: это тестовый переключатель, не проверка личности. Cookie HttpOnly/SameSite=strict; Secure отсутствует только для loopback HTTP. Перезапуск gateway сбрасывает сессии. Истечение 30мин, revoke действует для следующих запросов. Загруженные ранее браузером кадры нельзя вернуть/стереть.

```sh
RUN_IMAGING_LIVE=1 .venv/bin/pytest -q
.venv/bin/playwright install --with-deps chromium
.venv/bin/python browser_check.py
docker compose down
```

Для системного Chromium: `CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python browser_check.py`. Browser evidence: test-results/viewer.png (не коммитится). На CI живой тест и browser обязательны; обычный pytest без RUN_IMAGING_LIVE явно пропускает live test.

## Изоляция и данные

Только web имеет опубликованный порт, строго 127.0.0.1:8090. Web подключён к frontend bridge и внутренней сети; Orthanc/OHIF/gateway/seed только во внутренней сети. На этом Docker internal-only сеть не публиковала loopback-порт, поэтому отдельный bridge нужен только web. Orthanc HTTP auth выключена исключительно внутри disposable сети; DICOM listener выключен, REST не проброшен. Нет host mounts DICOM/NAS и persistent volumes: Orthanc DB — tmpfs. После пересоздания контейнера выполнить seed повторно.

Генератор synthetic.py создаёт два исследования по 8 срезов, 128×128, uncompressed Explicit VR Little Endian, CT Image Storage. Только круги с переменным радиусом, фиксированные UIDs и SYNTHETIC labels; никаких источников клинических данных. Генерация в памяти, .dcm не записываются в Git. Повторный seed идемпотентен по UID. Все образы pinned по digest, зависимости по uv.lock и requirements с хешами. Перегенерация: `uv export --frozen --no-dev --format requirements-txt > requirements.txt`, аналогично `--all-groups` для requirements-test.txt.

## Границы gateway

Разрешены только read-only QIDO заданного study, series/instance metadata и WADO instance/frames/1 из известных fixture UIDs. Неизвестная иерархия/серия/кадр, unscoped QIDO, глобальный поиск и STOW отвергаются. BulkDataURI удаляется: поддержаны только выбранные маленькие CT fixtures и frame endpoint. CORS не открыт, no-store; браузер CSP ограничен self. Внешние URL из query не проксируются. Авторизация проверяется до upstream и перед ответом.

OHIF делает дополнительный patient-history query `00100020`; ожидаемый 403 не мешает просмотру назначенного study. Нельзя разрешать этот query глобально ради удаления ошибки. Начальные подсказки OHIF можно закрыть вручную; investigational-use warning сохранён.

Ответы буферизуются; Range явно отклоняется 400 после проверки прав, а HEAD не декодирует пустое JSON-тело. Полноценной streaming/Range реализации нет. Нет PostgreSQL policy/audit, MFA, ZIP, production error/limit hardening или отмены большого активного потока. Это эксперимент в experiments/, не сервис приложения. Не подключать к нему реальные данные. Production gateway должен иметь отдельную реализацию на общей policy после auth/backend foundation.

## Результаты и критерии

Локально: 6 pytest checks PASS, QIDO scoped metadata8 instances, pixel bytes первого frame соответствуют генератору, foreign study403, revoke запрещает следующий frame и HEAD/Range. Browser загрузил8 кадров, canvas отрисовал геометрический круг; external requests0, JS errors0, revoke frame403. Скриншот просмотрен вручную. В версиях Starlette/TestClient есть deprecation warning про httpx2; тесты проходят, перед production backend выбрать согласованный набор зависимостей.

Техническое решение: Orthanc/DICOMweb/OHIF можно использовать для следующей стадии. Следующий этап — аккаунты и пароль+TOTP, PostgreSQL назначения и общая policy, затем перенос интеграции из эксперимента. Никакой migration/production deploy не выполнялся.
