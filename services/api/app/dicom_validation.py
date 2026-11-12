"""Bounded Part-10 import. Originals are never rewritten or extracted by archive paths."""

import hashlib
import re
import stat
import warnings
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath

import pydicom
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, ImplicitVRLittleEndian

UPLOAD_LIMIT = 32 * 1024 * 1024
EXPANDED_LIMIT = 64 * 1024 * 1024
INSTANCE_LIMIT = 16 * 1024 * 1024
FILE_LIMIT = 256
UID = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))+\Z")


class InvalidDicom(Exception):
    """Only a stable code is exposed; never include parser exceptions or filenames."""


@dataclass
class Validated:
    data: bytes
    study_uid: str
    series_uid: str
    sop_uid: str
    sha256: str


def valid_uid(value: str) -> bool:
    return len(value) <= 64 and UID.fullmatch(value) is not None


def validate(data: bytes, patient_id: str) -> Validated:
    if len(data) > INSTANCE_LIMIT or len(data) < 132 or data[128:132] != b"DICM":
        raise InvalidDicom("INVALID_DICOM")
    try:
        # Invalid values generate exceptions, not warnings containing medical values.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            ds = pydicom.dcmread(BytesIO(data), force=False)
            uids = [str(ds.StudyInstanceUID), str(ds.SeriesInstanceUID), str(ds.SOPInstanceUID)]
            if not all(valid_uid(uid) for uid in uids):
                raise InvalidDicom("INVALID_UID")
            if str(ds.PatientID) != patient_id:
                raise InvalidDicom("PATIENT_MISMATCH")
            if str(ds.file_meta.MediaStorageSOPInstanceUID) != uids[2]:
                raise InvalidDicom("INVALID_UID")
            # A deliberately small initial compatibility envelope, not a diagnostic validator.
            if (
                ds.file_meta.TransferSyntaxUID not in {ExplicitVRLittleEndian, ImplicitVRLittleEndian}
                or ds.SOPClassUID != CTImageStorage
                or ds.file_meta.MediaStorageSOPClassUID != ds.SOPClassUID
                or int(ds.get("NumberOfFrames", 1)) != 1
                or int(ds.SamplesPerPixel) != 1
                or int(ds.BitsAllocated) not in {8, 16}
                or ds.PhotometricInterpretation not in {"MONOCHROME1", "MONOCHROME2"}
            ):
                raise InvalidDicom("UNSUPPORTED_DICOM")
            rows, cols = int(ds.Rows), int(ds.Columns)
            expected = rows * cols * int(ds.BitsAllocated) // 8
            if not (0 < rows <= 4096 and 0 < cols <= 4096) or expected > INSTANCE_LIMIT:
                raise InvalidDicom("PIXEL_LIMIT")
            if len(ds.PixelData) != expected + expected % 2:
                raise InvalidDicom("INVALID_PIXELS")
            return Validated(data, uids[0], uids[1], uids[2], hashlib.sha256(data).hexdigest())
    except InvalidDicom:
        raise
    except Exception:
        raise InvalidDicom("INVALID_DICOM") from None


def read_upload(path: Path, kind: str, patient_id: str) -> list[Validated]:
    if path.stat().st_size > UPLOAD_LIMIT:
        raise InvalidDicom("UPLOAD_LIMIT")
    if kind == "dicom":
        return [validate(path.read_bytes(), patient_id)]
    result = []
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > FILE_LIMIT:
                raise InvalidDicom("ARCHIVE_LIMIT")
            total = 0
            for entry in entries:
                name = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                if (
                    name.is_absolute()
                    or ".." in name.parts
                    or "\\" in entry.filename
                    or ":" in entry.filename
                    or entry.is_dir()
                    or entry.flag_bits & 1
                    or stat.S_ISLNK(mode)
                    or (stat.S_IFMT(mode) not in {0, stat.S_IFREG})
                    or entry.file_size > INSTANCE_LIMIT
                    or entry.file_size > max(entry.compress_size, 1) * 100
                ):
                    raise InvalidDicom("UNSAFE_ARCHIVE")
                total += entry.file_size
                if total > EXPANDED_LIMIT:
                    raise InvalidDicom("ARCHIVE_LIMIT")
                with archive.open(entry) as source:
                    data = source.read(INSTANCE_LIMIT + 1)
                if len(data) != entry.file_size:
                    raise InvalidDicom("INVALID_ARCHIVE")
                result.append(validate(data, patient_id))
    except InvalidDicom:
        raise
    except Exception:
        raise InvalidDicom("INVALID_ARCHIVE") from None
    if len({item.study_uid for item in result}) != 1:
        raise InvalidDicom("MIXED_STUDIES")
    if len({item.sop_uid for item in result}) != len(result):
        raise InvalidDicom("DUPLICATE_INSTANCE")
    return result
