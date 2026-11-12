"""Real React selection regression; API entirely intercepted with synthetic fixtures, no DB access."""

import os
import signal
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:5175"
STUDIES = [
    {
        "id": f"00000000-0000-0000-0000-00000000000{n}",
        "patient_id": f"00000000-0000-0000-0000-00000000001{n}",
        "local_identifier": f"SYN-SELECTION-0{n}",
        "display_name": f"SYNTHETIC PATIENT 0{n}",
        "title": f"Тест 0{n}",
        "modality": "CBCT",
        "state": "REGISTERED",
        "created_at": f"2030-01-0{3 - n}T10:00:00Z",
    }
    for n in (1, 2)
]
with open("/tmp/familydent-context-selection-vite.log", "w") as log:
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", "5175", "--strictPort"],
        cwd=ROOT / "apps/web",
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    try:
        with httpx.Client(trust_env=False, timeout=2) as client:
            for _ in range(30):
                try:
                    if client.get(BASE).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError("Synthetic selection frontend unavailable")
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--no-proxy-server"])
            for role in ("doctor", "imaging_staff"):
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                details = []

                def route_api(route):
                    path = urlsplit(route.request.url).path
                    if path == "/api/auth/me":
                        data = {
                            "id": "synthetic-account",
                            "display_name": "SYNTHETIC USER",
                            "role": role,
                            "csrf_token": "synthetic-only",
                        }
                    elif path in ("/api/doctor/studies", "/api/staff/studies"):
                        data = {"items": STUDIES, "total": 2, "limit": 25, "offset": 0}
                    elif path == "/api/workspace/overview":
                        data = {"latest": STUDIES[0], "events": []}
                    elif path in ("/api/staff/doctors", "/api/clinics") or path.endswith("/assignments"):
                        details.append(path)
                        data = []
                    elif path.startswith("/api/doctor/studies/"):
                        details.append(path)
                        data = next(s for s in STUDIES if path.endswith(s["id"]))
                    else:
                        raise AssertionError("Unexpected synthetic API route")
                    route.fulfill(status=200, json=data)

                context.route("**/api/**", route_api)
                page = context.new_page()
                page.goto(BASE)
                card = page.locator(".recent-study")
                expect(card.get_by_role("heading", name="Тест 01", exact=True)).to_be_visible()
                page.get_by_role("button", name="Открыть SYN-SELECTION-02", exact=True).click()
                if role == "imaging_staff":
                    expect(page.get_by_role("dialog")).to_be_visible()
                    page.get_by_role("button", name="Закрыть форму", exact=True).click()
                else:
                    expect(
                        page.locator("#study-details").get_by_role("heading", name="Тест 02", exact=True)
                    ).to_be_visible()
                expect(card.get_by_role("heading", name="Тест 02", exact=True)).to_be_visible()
                expect(card.get_by_text("SYNTHETIC PATIENT 02", exact=True)).to_be_visible()
                expect(card.get_by_text("Выбранное исследование", exact=True)).to_be_visible()
                expect(page.locator('tr[aria-current="true"]')).to_have_count(1)
                expect(page.locator('tr[aria-current="true"]')).to_contain_text("SYN-SELECTION-02")
                card.get_by_role("button", name="Открыть исследование", exact=True).click()
                if role == "imaging_staff":
                    expect(
                        page.get_by_role("dialog").get_by_text("Тест 02 · SYN-SELECTION-02", exact=True)
                    ).to_be_visible()
                    page.get_by_role("button", name="Закрыть форму", exact=True).click()
                else:
                    expect(
                        page.locator("#study-details").get_by_role("heading", name="Тест 02", exact=True)
                    ).to_be_visible()
                    page.locator("#study-details").get_by_role("button", name="Закрыть", exact=True).click()
                assert details[-1].endswith(
                    STUDIES[1]["id"] + ("/assignments" if role == "imaging_staff" else "")
                )
                expect(card.get_by_role("heading", name="Тест 02", exact=True)).to_be_visible()
                page.get_by_role("button", name="Обновить", exact=True).click()
                expect(card.get_by_role("heading", name="Тест 01", exact=True)).to_be_visible()
                expect(card.get_by_text("Последнее поступление", exact=True)).to_be_visible()
                context.close()
                print(
                    f"PASS selected-card {role}: second row, correct action, close retains selection, refresh resets",
                    flush=True,
                )
            browser.close()
    finally:
        os.killpg(frontend.pid, signal.SIGTERM)
        frontend.wait(timeout=10)
