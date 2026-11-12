"""Disposable synthetic-only compatibility gateway. NOT production auth."""
from contextlib import asynccontextmanager
import secrets
import time
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from synthetic import STUDY_UID, SERIES_UID, COUNT, instance_uid


def permitted_path(path: str) -> bool:
    root = f'studies/{STUDY_UID}'
    if path in {root, root + '/metadata', root + '/series', root + '/instances', root + f'/series/{SERIES_UID}/metadata', root + f'/series/{SERIES_UID}/instances'}:
        return True
    for n in range(1, COUNT + 1):
        base = root + f'/series/{SERIES_UID}/instances/{instance_uid(n)}'
        if path in {base, base + '/metadata', base + '/frames/1'}:
            return True
    return False


@asynccontextmanager
async def lifespan(app):
    app.state.sessions = {}
    async with httpx.AsyncClient(base_url='http://orthanc:8042', trust_env=False, timeout=20) as client:
        app.state.upstream = client
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


def authorized(request):
    token = request.cookies.get('spike_session')
    session = app.state.sessions.get(token)
    if not session or session['until'] <= time.monotonic():
        raise HTTPException(401, 'Demo session required')
    if session['actor'] != 'a' or session['revoked']:
        raise HTTPException(403, 'Not permitted')


@app.middleware('http')
async def no_store(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.get('/demo')
def demo():
    return HTMLResponse('<h1>Synthetic imaging spike</h1><p>NOT FOR DIAGNOSIS. No clinical data. Demo sessions are not authentication.</p><a href="/demo/open?actor=a">Open assigned synthetic study</a>')


@app.get('/demo/open')
def open_demo(actor: str = 'a'):
    if actor not in ('a', 'b'):
        raise HTTPException(400)
    now = time.monotonic()
    app.state.sessions = {key: value for key, value in app.state.sessions.items() if value['until'] > now}
    token = secrets.token_urlsafe(32)
    app.state.sessions[token] = {'actor': actor, 'until': time.monotonic() + 1800, 'revoked': False}
    response = RedirectResponse('/viewer?StudyInstanceUIDs=' + STUDY_UID, status_code=303)
    response.set_cookie('spike_session', token, httponly=True, samesite='strict', max_age=1800)
    return response


@app.post('/demo/revoke')
def revoke(request: Request):
    # Same-origin only; local test mechanism, not a production permission endpoint.
    if request.headers.get('origin') != str(request.base_url).rstrip('/'):
        raise HTTPException(403)
    session = app.state.sessions.get(request.cookies.get('spike_session'))
    if not session:
        raise HTTPException(401)
    session['revoked'] = True
    return Response(status_code=204)


def rewrite_bulk(value):
    if isinstance(value, list):
        return [rewrite_bulk(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key == 'BulkDataURI':
                # No arbitrary upstream URI is passed to the browser. Pixel data uses frames.
                continue
            result[key] = rewrite_bulk(item)
        return result
    return value


@app.api_route('/dicom-web/{path:path}', methods=['GET', 'HEAD'])
async def dicomweb(path: str, request: Request):
    authorized(request)
    if 'range' in request.headers:
        raise HTTPException(400, 'Range unsupported in synthetic spike')
    query = list(request.query_params.multi_items())
    if path == 'studies':
        # No unscoped QIDO, including search/count queries. OHIF supplies this UID.
        if request.query_params.getlist('StudyInstanceUID') != [STUDY_UID]:
            raise HTTPException(403, 'Not permitted')
    elif not permitted_path(path):
        raise HTTPException(403, 'Not permitted')
    allowed = {'StudyInstanceUID', 'includefield', 'limit', 'offset', 'fuzzymatching'}
    if any(k not in allowed for k, v in query):
        raise HTTPException(400, 'Unsupported query')
    headers = {}
    if 'accept' in request.headers:
        headers['accept'] = request.headers['accept']
    try:
        upstream = await app.state.upstream.request(request.method, '/dicom-web/' + path, params=query, headers=headers)
    except httpx.HTTPError:
        raise HTTPException(502, 'Archive unavailable') from None
    authorized(request)  # Recheck after upstream retrieval, before returning bytes.
    if upstream.status_code >= 400:
        raise HTTPException(502, 'Archive request failed')
    if request.method == 'HEAD':
        return Response(status_code=upstream.status_code, media_type=upstream.headers.get('content-type'))
    if 'json' in upstream.headers.get('content-type', ''):
        from fastapi.responses import JSONResponse
        return JSONResponse(rewrite_bulk(upstream.json()), media_type='application/dicom+json')
    return Response(upstream.content, media_type=upstream.headers.get('content-type', 'application/octet-stream'))
