"""Quarantined imports and the explicitly published instance index."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dicom_import_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("study_id", sa.Uuid(), sa.ForeignKey("studies.id"), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("error_code", sa.String(40)),
        sa.Column("study_uid", sa.String(64)),
        sa.Column("zip_sha256", sa.String(64)),
        sa.Column("zip_size", sa.Integer()),
        sa.CheckConstraint("state IN ('QUEUED','REVIEW','FAILED','PUBLISHED')", name="import_state"),
        sa.CheckConstraint("kind IN ('dicom','zip')", name="import_kind"),
    )
    op.create_index("ix_dicom_import_jobs_study_id", "dicom_import_jobs", ["study_id"])
    op.create_table(
        "dicom_instances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("dicom_import_jobs.id"), nullable=False),
        sa.Column("study_id", sa.Uuid(), sa.ForeignKey("studies.id"), nullable=False),
        sa.Column("series_uid", sa.String(64), nullable=False),
        sa.Column("sop_uid", sa.String(64), unique=True, nullable=False),
        sa.Column("orthanc_id", sa.String(64), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.CheckConstraint("size > 0", name="instance_size"),
    )
    for col in ("job_id", "study_id", "series_uid"):
        op.create_index("ix_dicom_instances_" + col, "dicom_instances", [col])
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON dicom_import_jobs, dicom_instances TO familydent_app")


def downgrade():
    op.drop_table("dicom_instances")
    op.drop_table("dicom_import_jobs")
