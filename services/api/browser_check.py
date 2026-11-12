"""Full real browser flow against disposable test DB; never touches dev accounts."""

import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pyotp
import uvicorn
import zxingcpp
from alembic.config import Config
from PIL import Image
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings
from app.main import create_app
from app.models import Base, Clinic, Membership, User
from app.runtime import load_local_env
from app.security import hash_password
from app.synthetic_dicom import fixture

ROOT = Path(__file__).resolve().parents[2]
load_local_env()
assert os.environ["TEST_ADMIN_DATABASE_URL"].endswith("/familydent_test")
cfg = Config("alembic.ini")
cfg.attributes["database_url"] = os.environ["TEST_ADMIN_DATABASE_URL"]
command.upgrade(cfg, "head")
admin_engine = create_engine(os.environ["TEST_ADMIN_DATABASE_URL"], hide_parameters=True)
with admin_engine.begin() as connection:
    connection.execute(
        text("TRUNCATE " + ",".join('"' + t.name + '"' for t in Base.metadata.sorted_tables) + " CASCADE")
    )
admin_engine.dispose()
password = secrets.token_urlsafe(24)
engine = create_engine(os.environ["TEST_DATABASE_URL"], hide_parameters=True)
with Session(engine) as db, db.begin():
    clinic = Clinic(name="SYNTHETIC BROWSER CLINIC")
    db.add(clinic)
    db.flush()
    for name, role in [
        ("staff", "imaging_staff"),
        ("doctor", "doctor"),
        ("other", "doctor"),
        ("admin", "platform_admin"),
    ]:
        user = User(
            email=name + "@example.test",
            display_name="SYNTHETIC " + name,
            role=role,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()
        if role == "doctor":
            db.add(Membership(user_id=user.id, clinic_id=clinic.id))
engine.dispose()
imaging_directory = tempfile.TemporaryDirectory(prefix="familydent-synthetic-browser-")
settings = Settings(
    database_url=os.environ["TEST_DATABASE_URL"],
    totp_key=os.environ["TOTP_KEY"],
    auth_key=os.environ["AUTH_KEY"],
    public_origin="http://127.0.0.1:5174",
    development=True,
    imaging_root=imaging_directory.name,
)
app = create_app(settings)
server = uvicorn.Server(
    uvicorn.Config(app, host="127.0.0.1", port=8101, access_log=False, log_level="warning")
)
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
log = open("/tmp/familydent-browser-vite.log", "w")
frontend = subprocess.Popen(
    ["npm", "run", "dev", "--", "--port", "5174", "--strictPort"],
    cwd=ROOT / "apps/web",
    env={**os.environ, "API_PROXY_TARGET": "http://127.0.0.1:8101"},
    stdout=log,
    stderr=log,
)
try:
    with httpx.Client(trust_env=False, timeout=2) as client:
        for _ in range(60):
            try:
                if client.get("http://127.0.0.1:5174/api/health").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Test frontend/backend did not become ready")
    with sync_playwright() as p:
        options = {
            "args": [
                "--no-sandbox",
                "--no-proxy-server",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader",
            ]
        }
        if os.getenv("CHROMIUM_PATH"):
            options["executable_path"] = os.environ["CHROMIUM_PATH"]
        browser = p.chromium.launch(**options)
        errors, external = [], []

        def login(name):
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: (
                    external.append(request.url)
                    if not request.url.startswith(
                        ("http://127.0.0.1:5174", "http://127.0.0.1:8091", "blob:", "data:")
                    )
                    else None
                ),
            )
            page.goto("http://127.0.0.1:5174")
            page.get_by_label("Электронная почта").fill(name + "@example.test")
            page.get_by_label("Пароль", exact=True).fill(password)
            page.get_by_role("button", name="Продолжить", exact=True).click()
            key = page.get_by_label("Ключ настройки TOTP")
            expect(key).to_be_visible()
            secret = key.input_value()
            if name == "staff":
                page.set_viewport_size({"width": 390, "height": 844})
            qr = page.get_by_role("img", name="QR-код для настройки TOTP", exact=True)
            expect(qr).to_be_visible(timeout=3000)
            decoded = zxingcpp.read_barcodes(Image.open(BytesIO(qr.screenshot())))
            assert len(decoded) == 1, "Enrollment QR could not be decoded"
            uri = urlsplit(decoded[0].text)
            params = parse_qs(uri.query)
            assert uri.scheme == "otpauth" and uri.netloc == "totp", "Unexpected QR protocol"
            assert params.get("secret") == [secret], "QR does not match enrollment key"
            assert params.get("issuer") == ["FamilyDent Imaging"], "Unexpected issuer"
            qr_code = pyotp.parse_uri(decoded[0].text).at(datetime.now(UTC))
            page.get_by_label("Код аутентификатора", exact=True).fill(qr_code)
            page.get_by_role("button", name="Подтвердить вход", exact=True).click()
            expect(page.get_by_role("button", name="Выйти", exact=True, include_hidden=True)).to_be_attached()
            expect(qr).to_have_count(0)
            expect(key).to_have_count(0)
            page.set_viewport_size({"width": 1440, "height": 900})
            return page

        print("Browser checkpoint: MFA staff", flush=True)
        staff = login("staff")
        patient_form = staff.locator("section").filter(
            has=staff.get_by_role("heading", name="Зарегистрировать пациента", exact=True)
        )
        expect(staff.get_by_role("heading", name="Зарегистрировать пациента", exact=True)).to_have_count(0)
        expect(staff.get_by_role("heading", name="Зарегистрировать исследование", exact=True)).to_have_count(
            0
        )
        new_patient = staff.get_by_role("button", name="Новый пациент", exact=True)
        new_patient.click()
        expect(staff.get_by_role("dialog", name="Зарегистрировать пациента", exact=True)).to_be_visible()
        patient_form.get_by_label("Внутренний ID пациента").fill("SYN-BROWSER-001")
        patient_form.get_by_label("ФИО пациента").fill("SYNTHETIC BROWSER PATIENT")
        patient_form.get_by_role("button", name="Сохранить", exact=True).click()
        expect(patient_form.get_by_role("status")).to_have_text("Сохранено")
        staff.get_by_role("button", name="Закрыть форму", exact=True).click()
        expect(new_patient).to_be_focused()
        staff.get_by_role("button", name="Новое исследование", exact=True).click()
        study_form = staff.locator("section").filter(
            has=staff.get_by_role("heading", name="Зарегистрировать исследование", exact=True)
        )
        expect(
            study_form.get_by_text(
                "Пациент исследования: SYN-BROWSER-001 · SYNTHETIC BROWSER PATIENT", exact=True
            )
        ).to_be_visible()
        study_form.get_by_label("Исследование", exact=True).fill("SYNTHETIC BROWSER STUDY")
        study_form.get_by_role("button", name="Сохранить", exact=True).click()
        expect(study_form.get_by_role("status")).to_have_text("Сохранено")
        staff.get_by_role("button", name="Закрыть форму", exact=True).click()
        staff.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True).click()
        assignment_form = staff.locator("section").filter(
            has=staff.get_by_role("heading", name="Назначить врачу", exact=True)
        )
        expect(staff.get_by_role("dialog", name="Назначить врачу", exact=True)).to_be_visible()
        Path("test-results").mkdir(exist_ok=True)
        staff.screenshot(
            path="test-results/staff-before-assignment.png", full_page=True, mask=[staff.locator("input")]
        )
        assignment_form.get_by_role("combobox").select_option(label="SYNTHETIC doctor")
        assignment_form.get_by_role("button", name="Сохранить", exact=True).click()
        expect(assignment_form.get_by_role("button", name="Отозвать", exact=True)).to_be_visible()
        staff.get_by_role("button", name="Закрыть форму", exact=True).click()
        staff.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True).click()
        staff.get_by_role("button", name="Импорт DICOM", exact=True).click()
        print("Browser checkpoint: upload dialog", flush=True)
        for width in (320, 375, 414, 768, 1440):
            staff.set_viewport_size({"width": width, "height": 900})
            dropzone = staff.locator(".dicom-dropzone")
            expect(dropzone).to_be_visible()
            staff.get_by_label("DICOM или ZIP", exact=True).focus()
            assert dropzone.evaluate("el => getComputedStyle(el).outlineStyle") != "none"
            assert staff.get_by_role("dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
            staff.screenshot(path=f"test-results/upload-picker-{width}.png")
        staff.set_viewport_size({"width": 1440, "height": 900})
        payload = BytesIO()
        from uuid import uuid4

        study_uid = "2.25." + str(uuid4().int)
        with zipfile.ZipFile(payload, "w") as archive:
            for number in range(1, 9):
                archive.writestr(f"slice-{number}.dcm", fixture(number, "SYN-BROWSER-001", study_uid))
        staff.get_by_label("DICOM или ZIP", exact=True).set_input_files(
            {"name": "synthetic.zip", "mimeType": "application/zip", "buffer": payload.getvalue()}
        )
        expect(staff.locator(".dicom-dropzone").get_by_text("synthetic.zip", exact=True)).to_be_visible()
        # The response event fires on headers; only requestfinished guarantees its body is available.
        with staff.expect_event(
            "requestfinished",
            predicate=lambda r: r.method == "POST" and r.url.endswith("/imports"),
            timeout=15000,
        ) as finished:
            staff.get_by_role("button", name="Загрузить на проверку", exact=True).click()
        uploaded = finished.value.response()
        assert uploaded.status == 202
        study_id = uploaded.json()["study_id"]
        expect(staff.get_by_text("В очереди на проверку", exact=True)).to_be_visible()
        print("Browser checkpoint: worker start", flush=True)
        subprocess.run(
            [sys.executable, "-m", "app.worker", "--once"],
            env={
                **os.environ,
                "DATABASE_URL": os.environ["TEST_DATABASE_URL"],
                "PUBLIC_ORIGIN": "http://127.0.0.1:5174",
                "IMAGING_ROOT": imaging_directory.name,
            },
            check=True,
            timeout=75,
        )
        expect(staff.get_by_text("Ожидает подтверждения", exact=True)).to_be_visible(timeout=10000)
        print("Browser checkpoint: worker reviewed", flush=True)
        doctor = login("doctor")
        expect(doctor.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True)).to_be_visible()
        expect(doctor.get_by_role("article", name="Последнее поступление", exact=True)).to_be_visible()
        expect(doctor.get_by_role("region", name="Последние события", exact=True)).to_be_visible()
        doctor.get_by_role("article", name="Последнее поступление", exact=True).get_by_role(
            "button", name="Открыть исследование", exact=True
        ).click()
        expect(doctor.locator("#study-details")).to_be_visible()
        expect(doctor.get_by_text("Исследование открыто", exact=True)).to_be_visible()
        for width in (320, 375, 414, 768, 1440):
            doctor.set_viewport_size({"width": width, "height": 900})
            assert doctor.evaluate("document.documentElement.scrollWidth <= innerWidth")
            doctor.screenshot(path=f"test-results/context-rail-{width}.png", full_page=True)
        doctor.set_viewport_size({"width": 1440, "height": 900})
        doctor.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True).click()
        expect(doctor.get_by_text("Снимки ещё не подтверждены сотрудником.", exact=False)).to_be_visible()
        assert (
            doctor.context.request.get(f"http://127.0.0.1:5174/api/doctor/studies/{study_id}/imaging").status
            == 404
        )
        staff.get_by_role("checkbox").check()
        staff.get_by_role("button", name="Подтвердить исследование", exact=True).click()
        expect(staff.get_by_text("Доступно врачу", exact=True)).to_be_visible()
        for width in (320, 375, 768, 1440):
            staff.set_viewport_size({"width": width, "height": 900})
            assert staff.get_by_role("dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
            staff.screenshot(path=f"test-results/import-{width}.png")
        staff.set_viewport_size({"width": 1440, "height": 900})
        staff.get_by_role("button", name="Закрыть форму", exact=True).click()
        doctor.get_by_role("button", name="Обновить", exact=True).click()
        doctor.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True).click()
        expect(doctor.get_by_role("link", name="Открыть просмотр", exact=True)).to_be_visible()
        with doctor.expect_download() as received:
            doctor.get_by_role("link", name="Скачать DICOM", exact=True).click()
        import hashlib

        with zipfile.ZipFile(received.value.path()) as archive:
            assert sorted(hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()) == sorted(
                hashlib.sha256(fixture(n, "SYN-BROWSER-001", study_uid)).hexdigest() for n in range(1, 9)
            )
        print("Browser checkpoint: download verified", flush=True)
        viewer = doctor.context.new_page()
        frames = []
        viewer.on("response", lambda r: frames.append((r.status, r.url)) if "/frames/1" in r.url else None)
        viewer.on("pageerror", lambda error: errors.append(str(error)))
        viewer.on(
            "request",
            lambda r: (
                external.append(r.url)
                if not r.url.startswith(("http://127.0.0.1:8091", "blob:", "data:"))
                else None
            ),
        )
        viewer.goto(
            doctor.get_by_role("link", name="Открыть просмотр", exact=True).get_attribute("href"),
            timeout=60000,
        )
        viewer.wait_for_function(
            "performance.getEntriesByType('resource').some(r => r.name.includes('/frames/1'))", timeout=60000
        )
        viewer.locator("canvas").first.wait_for(timeout=30000)
        for text in ("Skip all", "Confirm and hide"):
            button = viewer.get_by_text(text, exact=True)
            if button.count() and button.first.is_visible():
                button.first.click()
        assert any(status == 200 for status, _ in frames), "Protected viewer did not load frames"
        assert "Generated circles" in viewer.locator("body").inner_text()
        assert viewer.locator("canvas").first.evaluate("c => c.width > 0 && c.height > 0")
        viewer.screenshot(path="test-results/protected-viewer.png")
        frame_url = next(url for status, url in frames if status == 200)
        print("Browser checkpoint: viewer rendered", flush=True)
        repeat = browser.new_page()
        repeat.goto("http://127.0.0.1:5174")
        repeat.get_by_label("Электронная почта").fill("doctor@example.test")
        repeat.get_by_label("Пароль", exact=True).fill(password)
        repeat.get_by_role("button", name="Продолжить", exact=True).click()
        expect(repeat.get_by_role("heading", name="Подтвердите вход", exact=True)).to_be_visible()
        expect(repeat.get_by_role("img", name="QR-код для настройки TOTP", exact=True)).to_have_count(0)
        expect(repeat.get_by_label("Ключ настройки TOTP")).to_have_count(0)
        repeat.close()
        other = login("other")
        expect(other.get_by_text("Назначенные исследования не найдены", exact=True)).to_be_visible()
        # Neither another browser nor membership in the same clinic grants study access.
        staff.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True).click()
        assignment_form.get_by_role("button", name="Отозвать", exact=True).click()
        expect(assignment_form.get_by_text("SYNTHETIC doctor · Отозвано", exact=True)).to_be_visible()
        staff.get_by_role("button", name="Закрыть форму", exact=True).click()
        assert viewer.context.request.get(frame_url).status == 404
        assert (
            viewer.context.request.get(
                f"http://127.0.0.1:8091/api/doctor/studies/{study_id}/originals",
                headers={"Range": "bytes=0-127"},
            ).status
            == 404
        )
        viewer.close()
        doctor.get_by_role("button", name="Обновить", exact=True).click()
        expect(doctor.get_by_text("Назначенные исследования не найдены", exact=True)).to_be_visible()
        expect(
            doctor.get_by_role("article", name="Последнее поступление", exact=True).get_by_role("button")
        ).to_have_count(0)
        print("Browser checkpoint: revoke verified", flush=True)
        admin = login("admin")
        expect(admin.get_by_role("heading", name="Команда и доступы", exact=True)).to_be_visible()
        assert admin.context.request.get("http://127.0.0.1:5174/api/doctor/studies").status == 403
        assert admin.get_by_role("dialog").count() == 0
        admin.get_by_role("button", name="Добавить аккаунт", exact=True).click()
        expect(admin.get_by_role("dialog", name="Создать проверенный аккаунт", exact=True)).to_be_visible()
        admin.keyboard.press("Escape")
        expect(admin.get_by_role("dialog")).to_have_count(0)
        expect(admin.get_by_role("button", name="Добавить аккаунт", exact=True)).to_be_focused()
        Path("test-results").mkdir(exist_ok=True)
        doctor.screenshot(path="test-results/doctor.png")
        staff.screenshot(path="test-results/staff.png", full_page=True)
        admin.screenshot(path="test-results/admin.png")
        admin.set_viewport_size({"width": 390, "height": 844})
        admin.screenshot(path="test-results/mobile.png", full_page=True)
        for role, page in (("staff", staff), ("doctor", doctor), ("admin", admin)):
            for width in (320, 360, 375, 390, 414, 430, 600, 768, 820, 1024, 1366, 1440, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                page.evaluate("window.scrollTo(0, 0)")
                button = page.get_by_role("button", name="Выйти", exact=True)
                expect(button).to_be_visible()
                expect(button).to_be_enabled()
                box = button.bounding_box()
                assert box and box["y"] < 90 and box["height"] >= 44, (
                    "Logout must be visible and touch-friendly"
                )
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                    f"Overflow: {role}/{width}"
                )
                # Convert resolved OKLCH colors through canvas, then measure WCAG sRGB contrast.
                ratio = button.evaluate("""el => {
                    const style = getComputedStyle(el), c = document.createElement('canvas');
                    c.width = c.height = 1; const ctx = c.getContext('2d');
                    const lum = color => { ctx.fillStyle = color; ctx.fillRect(0,0,1,1);
                        const rgb = [...ctx.getImageData(0,0,1,1).data].slice(0,3).map(v => {
                            const n=v/255; return n<=.04045 ? n/12.92 : ((n+.055)/1.055)**2.4;
                        }); return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]; };
                    const a=lum(style.color), b=lum(style.backgroundColor);
                    return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                }""")
                assert ratio >= 4.5, f"Logout contrast: {ratio}"
                page.screenshot(path=f"test-results/{role}-{width}.png", full_page=True)
                if role in ("staff", "admin"):
                    trigger = page.get_by_role(
                        "button", name="Новый пациент" if role == "staff" else "Добавить клинику", exact=True
                    )
                    trigger.click()
                    dialog = page.get_by_role("dialog")
                    expect(dialog).to_be_visible()
                    assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth"), (
                        "Dialog horizontal overflow"
                    )
                    assert dialog.bounding_box()["width"] <= width, "Dialog wider than viewport"
                    page.screenshot(path=f"test-results/{role}-dialog-{width}.png")
                    page.keyboard.press("Escape")
                    expect(dialog).to_have_count(0)
                    expect(trigger).to_be_focused()
        # A failed logout keeps the button usable; successful keyboard activation revokes the session.
        other.set_viewport_size({"width": 375, "height": 844})
        other.route(
            "**/api/auth/logout", lambda route: route.fulfill(status=503, json={"code": "UNAVAILABLE"})
        )
        exit_button = other.get_by_role("button", name="Выйти", exact=True)
        exit_button.click()
        expect(other.get_by_role("alert")).to_be_visible()
        expect(exit_button).to_be_enabled()
        other.unroute("**/api/auth/logout")
        exit_button.focus()
        exit_button.press("Tab")
        other.keyboard.press("Shift+Tab")
        expect(exit_button).to_be_focused()
        assert exit_button.evaluate("el => getComputedStyle(el).outlineStyle") != "none"
        exit_button.press("Enter")
        expect(other.get_by_role("heading", name="Вход в портал", exact=True)).to_be_visible()
        assert other.context.request.get("http://127.0.0.1:5174/api/auth/me").status == 401
        assert not errors, errors
        assert not external, external
        browser.close()
        print(
            "PASS browser: password/TOTP, upload/worker/review, protected OHIF frames, byte-exact ZIP, doctor isolation, frame/Range revoke, admin denied; external requests 0"
        )
except Exception as error:
    # Playwright assertion snapshots can include enrollment keys; never log those.
    raise RuntimeError(
        f"Synthetic browser check failed ({type(error).__name__}); no sensitive page snapshot logged"
    ) from None
finally:
    frontend.terminate()
    try:
        frontend.wait(timeout=10)
    except subprocess.TimeoutExpired:
        frontend.kill()
    log.close()
    server.should_exit = True
    thread.join(timeout=10)
    app.state.engine.dispose()
    imaging_directory.cleanup()
