from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PatientInput(Input):
    local_identifier: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=160)


class StudyInput(Input):
    patient_id: UUID
    title: str = Field(min_length=1, max_length=200)
    modality: Literal["CBCT", "OPG", "IO", "CT", "DX", "CR"]


class AssignmentInput(Input):
    doctor_id: UUID
    clinic_id: UUID


class ClinicInput(Input):
    name: str = Field(min_length=1, max_length=160)


class UserInput(Input):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=160)
    role: Literal["doctor", "imaging_staff"]
    password: SecretStr = Field(min_length=12, max_length=128)
    clinic_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str):
        value = value.lower()
        if value.count("@") != 1 or not all(value.split("@")) or any(c.isspace() for c in value):
            raise ValueError("Invalid email")
        return value


class AccountResponse(BaseModel):
    id: UUID
    display_name: str
    role: Literal["doctor", "imaging_staff", "platform_admin"]
    csrf_token: str


class StudySummary(BaseModel):
    id: UUID
    patient_id: UUID
    local_identifier: str
    display_name: str
    title: str
    modality: str
    state: Literal["REGISTERED", "READY", "BLOCKED"]
    created_at: str


class StudyPage(BaseModel):
    items: list[StudySummary]
    total: int
    limit: int
    offset: int
