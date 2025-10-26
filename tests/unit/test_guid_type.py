"""Unit tests for the GUID database type decorator."""
from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from prep.core.db_types import GUID


def test_guid_sqlite_round_trip(engine):
    if engine.dialect.name != "sqlite":
        pytest.skip("SQLite-only round trip test")

    metadata = sa.MetaData()
    guid_table = sa.Table(
        "guid_sqlite_test",
        metadata,
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(50)),
    )

    with engine.begin() as conn:
        guid_table.create(conn)
        try:
            first_id = uuid.uuid4()
            second_id = uuid.uuid4()

            conn.execute(guid_table.insert().values(id=first_id, name="uuid"))
            conn.execute(guid_table.insert().values(id=str(second_id), name="string"))

            rows = conn.execute(
                sa.select(guid_table.c.id, guid_table.c.name).order_by(guid_table.c.name)
            ).all()

            assert {row.name for row in rows} == {"string", "uuid"}
            assert rows[0].id in {first_id, second_id}
            assert rows[1].id in {first_id, second_id}
            assert isinstance(rows[0].id, uuid.UUID)
            assert isinstance(rows[1].id, uuid.UUID)
        finally:
            guid_table.drop(conn)


def test_guid_accepts_str_values(engine):
    metadata = sa.MetaData()
    guid_table = sa.Table(
        "guid_string_test",
        metadata,
        sa.Column("id", GUID(), primary_key=True),
    )

    with engine.begin() as conn:
        guid_table.create(conn)
        try:
            raw_value = "f497dd55-78a8-4d6f-86fd-6b890ee7e4e2"
            conn.execute(guid_table.insert().values(id=raw_value))
            fetched = conn.execute(sa.select(guid_table.c.id)).scalar_one()
            assert isinstance(fetched, uuid.UUID)
            assert str(fetched) == raw_value
        finally:
            guid_table.drop(conn)


@pytest.mark.requires_pg
def test_guid_uses_native_uuid_on_postgres(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL engine not configured")

    metadata = sa.MetaData()
    guid_table = sa.Table(
        "guid_pg_test",
        metadata,
        sa.Column("id", GUID(), primary_key=True),
    )

    with engine.begin() as conn:
        guid_table.create(conn)
        try:
            inspector = sa.inspect(conn)
            columns = inspector.get_columns("guid_pg_test")
            assert columns, "expected guid_pg_test to have at least one column"
            assert columns[0]["type"].__class__.__name__.lower() == "uuid"
        finally:
            guid_table.drop(conn)
