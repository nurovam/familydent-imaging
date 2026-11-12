"""Opt-in checks against the actual isolated Compose stack."""
from io import BytesIO
import os
import httpx
import pydicom
import pytest
from synthetic import STUDY_UID, SERIES_UID, FOREIGN_STUDY_UID, fixture, instance_uid

pytestmark = pytest.mark.skipif(os.getenv('RUN_IMAGING_LIVE') != '1', reason='requires synthetic Compose stack')


def test_real_qido_metadata_frames_and_revocation():
    with httpx.Client(base_url='http://127.0.0.1:8090', trust_env=False) as client:
        client.get('/demo/open')
        qido = client.get('/dicom-web/studies', params={'StudyInstanceUID': STUDY_UID, 'fuzzymatching': 'false'})
        assert qido.status_code == 200, qido.text
        assert len(qido.json()) == 1
        root = f'/dicom-web/studies/{STUDY_UID}'
        metadata = client.get(root + '/metadata')
        assert metadata.status_code == 200
        assert len(metadata.json()) == 8
        instance = root + f'/series/{SERIES_UID}/instances/{instance_uid(1)}'
        frame = client.get(instance + '/frames/1', headers={'Accept': 'multipart/related; type="application/octet-stream"; transfer-syntax=*'})
        assert frame.status_code == 200
        expected = pydicom.dcmread(BytesIO(fixture())).PixelData
        assert expected in frame.content
        assert client.get('/dicom-web/studies/' + FOREIGN_STUDY_UID + '/metadata').status_code == 403
        assert client.post('/demo/revoke', headers={'Origin': 'http://127.0.0.1:8090'}).status_code == 204
        assert client.get(instance + '/frames/1').status_code == 403
        assert client.head(instance, headers={'Range': 'bytes=0-10'}).status_code == 403
