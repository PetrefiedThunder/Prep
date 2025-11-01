"""Tests for the Alembic city metadata comparison helper."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.schema import CreateTable

from apps.sf_regulatory_service import models
from tools import alembic_city_check


@pytest.fixture()
def sqlite_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'sf_regulatory.db'}"


def _create_sf_schema(database_url: str) -> None:
    engine = alembic_city_check._create_engine(database_url)
    models.Base.metadata.create_all(engine)


def test_city_check_passes_for_matching_schema(sqlite_url: str) -> None:
    _create_sf_schema(sqlite_url)

    exit_code, messages = alembic_city_check.run_city_check("sf", database_url=sqlite_url)

    assert exit_code == 0
    assert messages == ["No schema differences detected for city 'sf'."]


def test_city_check_detects_type_mismatch(sqlite_url: str) -> None:
    _create_sf_schema(sqlite_url)
    engine = alembic_city_check._create_engine(sqlite_url)
    table = models.SFBookingCompliance.__table__
    ddl = str(CreateTable(table).compile(engine))
    mutated = ddl.replace("prebooking_status VARCHAR(6) NOT NULL", "prebooking_status INTEGER NOT NULL")
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE sf_booking_compliance")
        connection.exec_driver_sql(mutated)

    exit_code, messages = alembic_city_check.run_city_check("sf", database_url=sqlite_url)

    assert exit_code == 1
    diff_lines = messages[1:]
    assert any("prebooking_status" in line and "INTEGER" in line for line in diff_lines)


def test_city_check_detects_default_difference(sqlite_url: str) -> None:
    _create_sf_schema(sqlite_url)
    engine = alembic_city_check._create_engine(sqlite_url)
    table = models.SFHostProfile.__table__
    ddl = str(CreateTable(table).compile(engine))
    mutated = ddl.replace(" DEFAULT 'flagged'", "")
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE sf_host_profiles")
        connection.exec_driver_sql(mutated)

    exit_code, messages = alembic_city_check.run_city_check("sf", database_url=sqlite_url)

    assert exit_code == 1
    diff_lines = messages[1:]
    assert any("Default mismatch" in line and "compliance_status" in line for line in diff_lines)
