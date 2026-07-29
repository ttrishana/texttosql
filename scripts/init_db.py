"""Create the schema and load synthetic data.

Single-DB (default):        one `firmdb` with all 19 tables.
Multi-DB (MULTI_DB=true):   one database per source in knowledge/sources.yaml,
                            each with its domain's tables (cross-domain FKs dropped).

Usage:
    python scripts/init_db.py                # full dataset
    python scripts/init_db.py --scale 0.2    # ~1/5th size for quick local runs

Prereqs: a reachable Postgres (Docker, embedded via EMBEDDED_DB=true, or your own
via scripts/bootstrap_db.py).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import MetaData, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from texttosql.config import get_settings  # noqa: E402
from texttosql.db.engine import get_admin_engine  # noqa: E402
from texttosql.db.schema_split import domain_ddl  # noqa: E402
from texttosql.db.seed import build_tables  # noqa: E402

SCHEMA_SQL = Path(__file__).resolve().parent.parent / "src" / "texttosql" / "db" / "schema.sql"


def _insert(engine, tables: list[str], data: dict[str, list[dict]]) -> dict[str, int]:
    meta = MetaData()
    meta.reflect(bind=engine)
    counts: dict[str, int] = {}
    with engine.begin() as conn:
        for name in tables:
            rows = data.get(name, [])
            if rows:
                conn.execute(meta.tables[name].insert(), rows)
            counts[name] = len(rows)
    return counts


def _init_single(scale: float) -> None:
    from texttosql.db.seed import seed

    engine = get_admin_engine()
    print("Creating schema (single database: firmdb) ...")
    with engine.begin() as conn:
        conn.execute(text("SET default_transaction_read_only = off"))
        conn.exec_driver_sql(SCHEMA_SQL.read_text())

    print(f"Seeding data (scale={scale}) ... this may take a minute.")
    counts = seed(engine, scale=scale)
    _report({"firmdb": counts})


def _init_multi(scale: float) -> None:
    from texttosql.knowledge.registry import get_registry

    if not get_settings().embedded_db:
        print("MULTI_DB=true without EMBEDDED_DB: point sources.yaml at your own\n"
              "databases (url / url_env) and load them yourself. init_db seeds only\n"
              "the embedded demo, so there is nothing to do here.")
        return

    from texttosql.db.embedded import ensure_database

    registry = get_registry()
    print(f"Generating dataset (scale={scale}) ...")
    data = dict(build_tables(scale=scale))

    grouped: dict[str, dict[str, int]] = {}
    for name in registry.names():
        source = registry.get(name)
        db = source.database
        print(f"\n[{name}] -> database '{db}': {len(source.tables)} tables")
        ensure_database(db)
        engine = get_admin_engine(db)

        with engine.begin() as conn:
            conn.execute(text("SET default_transaction_read_only = off"))
            for tbl in reversed(source.tables):  # drop children before parents
                conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{tbl}" CASCADE')
            for stmt in domain_ddl(source.tables):
                conn.exec_driver_sql(stmt)

        grouped[f"{name} ({db})"] = _insert(engine, source.tables, data)

    _report(grouped)


def _report(grouped: dict[str, dict[str, int]]) -> None:
    print("\nDone. Row counts:")
    for group, counts in grouped.items():
        print(f"\n  {group}")
        for table, n in counts.items():
            print(f"    {table:<22} {n:>8,}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=1.0, help="Row-volume scale (default 1.0).")
    args = parser.parse_args()

    if get_settings().multi_db:
        _init_multi(args.scale)
    else:
        _init_single(args.scale)


if __name__ == "__main__":
    main()
