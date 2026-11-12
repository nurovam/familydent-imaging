"""Deterministic geometric CT fixtures, generated in memory; never clinical data."""
from io import BytesIO
from struct import pack
import httpx
import time
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian

STUDY_UID = '2.25.20261112001'
SERIES_UID = STUDY_UID + '.1'
FOREIGN_STUDY_UID = '2.25.20261112002'
COUNT = 8


def instance_uid(number):
    return SERIES_UID + f'.{number}'


def fixture(number=1, foreign=False):
    study = FOREIGN_STUDY_UID if foreign else STUDY_UID
    sop = study + f'.1.{number}'
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = CTImageStorage
    meta.MediaStorageSOPInstanceUID = sop
    meta.ImplementationClassUID = '2.25.20261112999'
    ds = FileDataset(None, {}, file_meta=meta, preamble=b'\0' * 128)
    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = sop
    ds.StudyInstanceUID = study
    ds.SeriesInstanceUID = study + '.1'
    ds.FrameOfReferenceUID = study + '.9'
    ds.PatientName = 'SYNTHETIC^GEOMETRY'
    ds.PatientID = 'SYNTHETIC-ONLY'
    ds.PatientBirthDate = ''
    ds.PatientSex = 'O'
    ds.StudyDate = '20261112'
    ds.StudyTime = '120000'
    ds.StudyID = 'SYNTHETIC'
    ds.AccessionNumber = 'SYNTHETIC'
    ds.StudyDescription = 'SYNTHETIC GEOMETRY - NOT FOR DIAGNOSIS'
    ds.SeriesDescription = 'Generated circles'
    ds.Modality = 'CT'
    ds.Manufacturer = 'SYNTHETIC GENERATOR'
    ds.SeriesNumber = 1
    ds.InstanceNumber = number
    ds.ImageType = ['ORIGINAL', 'PRIMARY', 'AXIAL']
    ds.ImagePositionPatient = [0, 0, number * 2]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.PixelSpacing = [1, 1]
    ds.SliceThickness = 2
    ds.SpacingBetweenSlices = 2
    ds.Rows = ds.Columns = 128
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.BitsAllocated = ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.RescaleIntercept = 0
    ds.RescaleSlope = 1
    ds.WindowCenter = 0
    ds.WindowWidth = 1600
    radius = 24 + number * 2
    values = [700 if (x - 64)**2 + (y - 64)**2 < radius**2 else -800 for y in range(128) for x in range(128)]
    ds.PixelData = pack('<' + 'h' * len(values), *values)
    out = BytesIO()
    ds.save_as(out, enforce_file_format=True)
    return out.getvalue()


if __name__ == '__main__':
    with httpx.Client(base_url='http://orthanc:8042', trust_env=False) as client:
        for attempt in range(60):
            try:
                client.get('/system').raise_for_status()
                break
            except httpx.HTTPError:
                time.sleep(1)
        else:
            raise SystemExit('Synthetic Orthanc did not become ready')
        for foreign in (False, True):
            for number in range(1, COUNT + 1):
                response = client.post('/instances', content=fixture(number, foreign))
                response.raise_for_status()
    print('Seeded two fully synthetic studies, 8 slices each')
