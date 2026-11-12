"""Deterministic geometric CT fixtures, generated in memory; never clinical data."""

from io import BytesIO
from struct import pack

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import UID, CTImageStorage, ExplicitVRLittleEndian

STUDY_UID = "2.25.20261112001"
SERIES_UID = STUDY_UID + ".1"
FOREIGN_STUDY_UID = "2.25.20261112002"
COUNT = 8


def instance_uid(number):
    return SERIES_UID + f".{number}"


def fixture(number=1, patient_id="SYN-DEMO-001", study_uid=STUDY_UID):
    study = study_uid
    sop = study + f".1.{number}"
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = CTImageStorage
    meta.MediaStorageSOPInstanceUID = sop
    meta.ImplementationClassUID = UID("2.25.20261112999")
    ds = FileDataset(BytesIO(), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = sop
    ds.StudyInstanceUID = study
    ds.SeriesInstanceUID = study + ".1"
    ds.FrameOfReferenceUID = study + ".9"
    ds.PatientName = "SYNTHETIC^GEOMETRY"
    ds.PatientID = patient_id
    ds.PatientBirthDate = ""
    ds.PatientSex = "O"
    ds.StudyDate = "20261112"
    ds.StudyTime = "120000"
    ds.StudyID = "SYNTHETIC"
    ds.AccessionNumber = "SYNTHETIC"
    ds.StudyDescription = "SYNTHETIC GEOMETRY - NOT FOR DIAGNOSIS"
    ds.SeriesDescription = "Generated circles"
    ds.Modality = "CT"
    ds.Manufacturer = "SYNTHETIC GENERATOR"
    ds.SeriesNumber = 1
    ds.InstanceNumber = number
    ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]
    ds.ImagePositionPatient = [0, 0, number * 2]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.PixelSpacing = [1, 1]
    ds.SliceThickness = 2
    ds.SpacingBetweenSlices = 2
    ds.Rows = ds.Columns = 128
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.RescaleIntercept = 0
    ds.RescaleSlope = 1
    ds.WindowCenter = 0
    ds.WindowWidth = 1600
    radius = 24 + number * 2
    values = [
        700 if (x - 64) ** 2 + (y - 64) ** 2 < radius**2 else -800 for y in range(128) for x in range(128)
    ]
    ds.PixelData = pack("<" + "h" * len(values), *values)
    out = BytesIO()
    ds.save_as(out, enforce_file_format=True)
    return out.getvalue()


if __name__ == "__main__":
    import argparse
    import zipfile
    from pathlib import Path
    from uuid import uuid4

    parser = argparse.ArgumentParser(description="Generate only geometric synthetic DICOM; no clinical input")
    parser.add_argument("--patient-id", default="SYN-DEMO-001")
    args = parser.parse_args()
    if not args.patient_id.startswith("SYN-"):
        raise SystemExit("Synthetic IDs must begin SYN-")
    target = Path(__file__).resolve().parents[3] / "infra/local/synthetic-upload.zip"
    uid = "2.25." + str(uuid4().int)
    with zipfile.ZipFile(target, "w") as archive:
        for n in range(1, 9):
            archive.writestr(f"slice-{n}.dcm", fixture(n, args.patient_id, uid))
    target.chmod(0o600)
    print("Generated infra/local/synthetic-upload.zip, 8 geometric CT slices; not for diagnosis")
