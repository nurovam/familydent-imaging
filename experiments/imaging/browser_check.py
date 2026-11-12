"""Browser assertions against the actual synthetic-only local viewer."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    options = {'args': ['--no-sandbox', '--no-proxy-server', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']}
    if os.getenv('CHROMIUM_PATH'):
        options['executable_path'] = os.environ['CHROMIUM_PATH']
    browser = p.chromium.launch(**options)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    responses, errors, external = [], [], []
    page.on('response', lambda r: responses.append([r.status, r.url]) if '/dicom-web/' in r.url else None)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: external.append(r.url) if not r.url.startswith(('http://127.0.0.1:8090', 'blob:', 'data:')) else None)
    try:
        page.goto('http://127.0.0.1:8090/demo/open', wait_until='networkidle', timeout=60000)
        page.wait_for_function("performance.getEntriesByType('resource').some(r => r.name.includes('/frames/1'))", timeout=60000)
        page.locator('canvas').first.wait_for(timeout=30000)
        for text in ('Skip all', 'Confirm and hide'):
            button = page.get_by_text(text, exact=True)
            if button.count() and button.first.is_visible():
                button.first.click()
        assert any(code == 200 and '/frames/1' in url for code, url in responses), responses
        assert not errors, errors
        assert not external, external
        assert all(code == 200 or (code == 403 and '00100020=' in url) for code, url in responses), responses
        assert 'Generated circles' in page.locator('body').inner_text()
        assert page.locator('canvas').first.evaluate('(c) => c.width > 0 && c.height > 0')
        request = page.context.request
        assert request.post('http://127.0.0.1:8090/demo/revoke', headers={'Origin': 'http://127.0.0.1:8090'}).status == 204
        frame_url = next(url for code, url in responses if '/frames/1' in url)
        assert request.get(frame_url).status == 403
        print(json.dumps({'frames_loaded': sum(code == 200 and '/frames/1' in url for code, url in responses), 'pageerrors': errors, 'external': external, 'revoked_frame_status': 403}))
    finally:
        Path('test-results').mkdir(exist_ok=True)
        page.screenshot(path='test-results/viewer.png')
        browser.close()
