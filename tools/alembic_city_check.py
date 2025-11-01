"""Utility to compare city-specific metadata against the database."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, List, Sequence

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.sql.schema import Constraint, Index, Table


SUPPORTED_CITIES = ("sf",)


def _load_city_metadata(city: str):
    if city == "sf":
        from apps.sf_regulatory_service import models

        return models.Base.metadata
    raise ValueError(f"Unsupported city '{city}'. Supported cities: {', '.join(SUPPORTED_CITIES)}")


def _resolve_database_url(city: str, override: str | None) -> str:
    if override:
        return override
    if city == "sf":
        from apps.sf_regulatory_service import database

        return os.getenv(database.DATABASE_URL_ENV, database.DEFAULT_DATABASE_URL)
    raise ValueError(f"Unsupported city '{city}'.")


def _create_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def _target_table_names(metadata) -> set[str]:
    return {table.name for table in metadata.sorted_tables}


def _resolve_table_name(obj: object | None) -> str | None:
    if obj is None:
        return None
    table = getattr(obj, "table", None)
    if table is not None and isinstance(table, Table):
        return table.name
    parent = getattr(obj, "parent", None)
    if isinstance(parent, Table):
        return parent.name
    if isinstance(obj, Table):
        return obj.name
    return None


def _include_object_factory(target_tables: set[str]):
    def include_object(object_, name, type_, reflected, compare_to):  # pragma: no cover - exercised indirectly
        if type_ == "table":
            return name in target_tables
        table_name = _resolve_table_name(object_) or _resolve_table_name(compare_to)
        if table_name is None:
            return True
        return table_name in target_tables

    return include_object


def _format_type(type_) -> str:
    try:
        return str(type_)
    except Exception:  # pragma: no cover - defensive formatting
        return type_.__class__.__name__


def _format_constraint(constraint: Constraint) -> str:
    name = getattr(constraint, "name", None)
    pieces = [constraint.__class__.__name__]
    if name:
        pieces.append(f"'{name}'")
    table = _resolve_table_name(constraint)
    if table:
        pieces.append(f"on {table}")
    if hasattr(constraint, "columns"):
        cols = ", ".join(col.name for col in constraint.columns)
        if cols:
            pieces.append(f"({cols})")
    if hasattr(constraint, "ondelete") and constraint.ondelete:
        pieces.append(f"ondelete={constraint.ondelete}")
    if hasattr(constraint, "onupdate") and constraint.onupdate:
        pieces.append(f"onupdate={constraint.onupdate}")
    return " ".join(pieces)


def _format_index(index: Index) -> str:
    cols = ", ".join(col.name for col in index.columns)
    return f"Index '{index.name}' on ({cols})"


def _format_diff(diff) -> str:
    op = diff[0]
    if op == "add_table":
        table: Table = diff[1]
        return f"Table '{table.name}' missing from database"
    if op == "remove_table":
        table: Table = diff[1]
        return f"Table '{table.name}' exists in database but not metadata"
    if op == "add_column":
        table_name, column, schema = diff[1], diff[2], diff[3]
        return f"Column '{column.name}' missing from table '{table_name}' (schema={schema})"
    if op == "remove_column":
        table_name, column, schema = diff[1], diff[2], diff[3]
        return f"Column '{column.name}' unexpectedly present in table '{table_name}' (schema={schema})"
    if op == "modify_type":
        table_name, column_name, existing_type, desired_type, schema = diff[1:6]
        return (
            f"Type mismatch on {table_name}.{column_name}: database has {_format_type(existing_type)}, "
            f"expected {_format_type(desired_type)} (schema={schema})"
        )
    if op == "modify_nullable":
        table_name, column_name, existing_nullable, desired_nullable, schema = diff[1:6]
        return (
            f"Nullability mismatch on {table_name}.{column_name}: database allows {existing_nullable}, "
            f"expected {desired_nullable} (schema={schema})"
        )
    if op == "modify_default":
        table_name, column_name, existing_default, desired_default, schema = diff[1:6]
        return (
            f"Default mismatch on {table_name}.{column_name}: database default {existing_default}, "
            f"expected {desired_default} (schema={schema})"
        )
    if op in {"add_constraint", "remove_constraint", "add_fk", "remove_fk"}:
        table_name, constraint = diff[1], diff[2]
        verb = {
            "add_constraint": "Missing",
            "remove_constraint": "Unexpected",
            "add_fk": "Missing",
            "remove_fk": "Unexpected",
        }[op]
        return f"{verb} constraint on table '{table_name}': {_format_constraint(constraint)}"
    if op in {"add_index", "remove_index"}:
        table_name, index = diff[1], diff[2]
        verb = "Missing" if op == "add_index" else "Unexpected"
        return f"{verb} { _format_index(index) } on table '{table_name}'"
    if op == "modify_check_constraint":
        table_name, constraint, action = diff[1:4]
        return f"Check constraint change on '{table_name}': {action} {_format_constraint(constraint)}"
    return repr(diff)


def _compare_with_metadata(engine: Engine, metadata) -> List[str]:
    target_tables = _target_table_names(metadata)
    include_object = _include_object_factory(target_tables)
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "include_object": include_object,
            },
        )
        diffs = compare_metadata(context, metadata)

    return [_format_diff(diff) for diff in diffs]


def run_city_check(city: str, database_url: str | None = None) -> tuple[int, List[str]]:
    metadata = _load_city_metadata(city)
    url = _resolve_database_url(city, database_url)
    engine = _create_engine(url)
    diffs = _compare_with_metadata(engine, metadata)
    if not diffs:
        return 0, [f"No schema differences detected for city '{city}'."]
    header = f"Schema differences for city '{city}':"
    return 1, [header, *differences_with_bullet(diffs)]


def differences_with_bullet(diffs: Sequence[str]) -> List[str]:
    return [f"- {line}" for line in diffs]


def _print_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare Alembic metadata for a given city.")
    parser.add_argument("--city", required=True, choices=SUPPORTED_CITIES, help="City identifier to validate.")
    parser.add_argument(
        "--database-url",
        dest="database_url",
        help="Optional SQLAlchemy URL to use instead of the city default.",
    )
    args = parser.parse_args(argv)

    exit_code, messages = run_city_check(args.city, args.database_url)
    _print_lines(messages)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
