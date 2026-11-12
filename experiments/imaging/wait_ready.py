"""Bounded readiness wait; errors never turn into a false pass."""
import time
import httpx

with httpx.Client(trust_env=False, timeout=2) as client:
    for attempt in range(60):
        try:
            response = client.get('http://127.0.0.1:8090/demo')
            if response.status_code == 200:
                print('Gateway ready')
                break
        except httpx.HTTPError:
            pass
        time.sleep(1)
    else:
        raise SystemExit('Gateway did not become ready')
