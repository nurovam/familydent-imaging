"""Record identifiers of changed permissions without credentials or medical payloads."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    for name, target in [
        ("target_user_id", "users"),
        ("target_clinic_id", "clinics"),
        ("assignment_id", "assignments"),
        ("patient_id", "patients"),
    ]:
        op.add_column("audit_events", sa.Column(name, sa.Uuid(), nullable=True))
        op.create_foreign_key("audit_" + name, "audit_events", target, [name], ["id"])


def downgrade():
    for name in ["patient_id", "assignment_id", "target_clinic_id", "target_user_id"]:
        op.drop_constraint("audit_" + name, "audit_events", type_="foreignkey")
        op.drop_column("audit_events", name)
