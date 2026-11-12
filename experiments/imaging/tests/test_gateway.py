from fastapi.testclient import TestClient
from gateway import app
from synthetic import STUDY_UID


def test_anonymous_foreign_uid_and_write_are_denied():
    with TestClient(app) as client:
        assert client.get('/dicom-web/studies').status_code == 401
        client.get('/demo/open', follow_redirects=False)
        assert client.get('/dicom-web/studies').status_code == 403
        assert client.get('/dicom-web/studies/9/metadata').status_code == 403
        assert client.post('/dicom-web/studies').status_code == 405
        assert client.get('/dicom-web/studies/' + STUDY_UID + '/metadata?url=http://evil').status_code == 400
        assert client.post('/demo/revoke', headers={'Origin': 'http://evil'}).status_code == 403
        assert client.post('/demo/revoke', headers={'Origin': 'http://testserver'}).status_code == 204
        assert client.get('/dicom-web/studies/' + STUDY_UID + '/metadata').status_code == 403


def test_other_doctor_and_expired_session_are_denied():
    with TestClient(app) as client:
        client.get('/demo/open?actor=b', follow_redirects=False)
        assert client.get('/dicom-web/studies/' + STUDY_UID + '/metadata').status_code == 403
        for session in app.state.sessions.values():
            session['until'] = 0
        assert client.get('/dicom-web/studies/' + STUDY_UID + '/metadata').status_code == 401


def test_head_and_unsupported_range_are_explicit():
    import httpx
    with TestClient(app) as client:
        client.get('/demo/open', follow_redirects=False)
        app.state.upstream = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={'Content-Type': 'application/dicom+json'})
        ), base_url='http://orthanc:8042')
        root = '/dicom-web/studies/' + STUDY_UID
        assert client.head(root + '/metadata').status_code == 200
        assert client.get(root, headers={'Range': 'bytes=0-10'}).status_code == 400


def test_revoke_during_upstream_retrieval_returns_no_payload():
    import httpx
    with TestClient(app) as client:
        client.get('/demo/open', follow_redirects=False)
        def revoke_during_request(request):
            for session in app.state.sessions.values():
                session['revoked'] = True
            return httpx.Response(200, content=b'PRIVATE_SYNTHETIC_BYTES')
        app.state.upstream = httpx.AsyncClient(transport=httpx.MockTransport(revoke_during_request), base_url='http://orthanc:8042')
        response = client.get('/dicom-web/studies/' + STUDY_UID)
        assert response.status_code == 403
        assert b'PRIVATE_SYNTHETIC_BYTES' not in response.content
