import os

from alembic.config import Config
from sqlalchemy import text

from alembic import command


def test_migration_roundtrip_on_disposable_test_database(engines):
    url = os.environ["TEST_ADMIN_DATABASE_URL"]
    assert url.endswith("/familydent_test")
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = url
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.check(cfg)
    with engines[1].connect() as connection:
        assert connection.scalar(text("SELECT has_table_privilege(current_user, 'audit_events', 'INSERT')"))
        assert not connection.scalar(
            text("SELECT has_table_privilege(current_user, 'audit_events', 'UPDATE')")
        )
        assert not connection.scalar(
            text("SELECT has_table_privilege(current_user, 'audit_events', 'DELETE')")
        )
        assert not connection.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user"))
