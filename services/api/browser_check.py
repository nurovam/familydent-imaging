"""Full real browser flow against disposable test DB; never touches dev accounts."""

import os
import secrets
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyotp
import uvicorn
from alembic.config import Config
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings
from app.main import create_app
from app.models import Base, Clinic, Membership, User
from app.runtime import load_local_env
from app.security import hash_password

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
settings = Settings(
    database_url=os.environ["TEST_DATABASE_URL"],
    totp_key=os.environ["TOTP_KEY"],
    auth_key=os.environ["AUTH_KEY"],
    public_origin="http://127.0.0.1:5174",
    development=True,
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
        options = {"args": ["--no-sandbox", "--no-proxy-server"]}
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
                    if not request.url.startswith(("http://127.0.0.1:5174", "blob:", "data:"))
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
            page.get_by_label("Код аутентификатора", exact=True).fill(
                pyotp.TOTP(secret).at(datetime.now(UTC))
            )
            page.get_by_role("button", name="Подтвердить вход", exact=True).click()
            expect(page.get_by_role("button", name="Выйти", exact=True)).to_be_attached()
            return page

        staff = login("staff")
        patient_form = staff.locator("section").filter(
            has=staff.get_by_role("heading", name="Зарегистрировать пациента", exact=True)
        )
        patient_form.get_by_label("Внутренний ID пациента").fill("SYN-BROWSER-001")
        patient_form.get_by_label("ФИО пациента").fill("SYNTHETIC BROWSER PATIENT")
        patient_form.get_by_role("button", name="Сохранить", exact=True).click()
        expect(patient_form.get_by_role("status")).to_have_text("Сохранено")
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
        staff.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True).click()
        assignment_form = staff.locator("section").filter(
            has=staff.get_by_role("heading", name="Назначить врачу", exact=True)
        )
        Path("test-results").mkdir(exist_ok=True)
        staff.screenshot(
            path="test-results/staff-before-assignment.png", full_page=True, mask=[staff.locator("input")]
        )
        assignment_form.get_by_role("combobox").select_option(label="SYNTHETIC doctor")
        assignment_form.get_by_role("button", name="Сохранить", exact=True).click()
        expect(assignment_form.get_by_role("button", name="Отозвать", exact=True)).to_be_visible()
        doctor = login("doctor")
        expect(doctor.get_by_role("button", name="Открыть SYN-BROWSER-001", exact=True)).to_be_visible()
        other = login("other")
        expect(other.get_by_text("Назначенные исследования не найдены", exact=True)).to_be_visible()
        # Neither another browser nor membership in the same clinic grants study access.
        assignment_form.get_by_role("button", name="Отозвать", exact=True).click()
        expect(assignment_form.get_by_text("SYNTHETIC doctor · Отозвано", exact=True)).to_be_visible()
        doctor.get_by_role("button", name="Обновить", exact=True).click()
        expect(doctor.get_by_text("Назначенные исследования не найдены", exact=True)).to_be_visible()
        admin = login("admin")
        expect(admin.get_by_role("heading", name="Команда и доступы", exact=True)).to_be_visible()
        assert admin.context.request.get("http://127.0.0.1:5174/api/doctor/studies").status == 403
        Path("test-results").mkdir(exist_ok=True)
        doctor.screenshot(path="test-results/doctor.png")
        staff.screenshot(path="test-results/staff.png", full_page=True)
        admin.screenshot(path="test-results/admin.png")
        admin.set_viewport_size({"width": 390, "height": 844})
        admin.screenshot(path="test-results/mobile.png", full_page=True)
        assert not errors, errors
        assert not external, external
        browser.close()
        print(
            "PASS browser: password/TOTP, staff registration/assignment, doctor isolation, revoke, admin denied medical access; external requests 0"
        )
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
