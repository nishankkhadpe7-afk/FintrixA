#!/usr/bin/env python3
"""Copy local SQLite data into a PostgreSQL database (for Supabase cutover).

Usage example:
    python scripts/migrate_sqlite_to_postgres.py \
        --target-url "postgresql+psycopg2://user:pass@host:6543/postgres?sslmode=require"

Notes:
- Run Alembic on target first: `alembic upgrade head`
- This script skips `alembic_version`
- Use --truncate-target to clear target tables before copy
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _default_source_sqlite() -> Path:
    # .../Backend/fintrix-api/scripts -> workspace root -> Database/s92.db
    workspace_root = Path(__file__).resolve().parents[3]
    return workspace_root / "Database" / "s92.db"


def _chunk_rows(rows: List[Dict], size: int = 500) -> List[List[Dict]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def migrate(source_sqlite: Path, target_url: str, truncate_target: bool) -> None:
    source_url = f"sqlite:///{source_sqlite.as_posix()}"

    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)

    source_meta = MetaData()
    target_meta = MetaData()

    source_meta.reflect(bind=source_engine)
    target_meta.reflect(bind=target_engine)

    source_tables = [
        table for table in source_meta.sorted_tables if table.name != "alembic_version"
    ]

    if not source_tables:
        print("No source tables found to migrate.")
        return

    print(f"Source DB: {source_sqlite}")
    print(f"Target DB: {target_url.split('@')[-1] if '@' in target_url else 'configured'}")
    print(f"Tables discovered: {len(source_tables)}")

    copied_totals: Dict[str, int] = {}

    try:
        with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
            if truncate_target:
                print("Truncating target tables...")
                for table in reversed(source_tables):
                    if table.name not in target_meta.tables:
                        continue
                    target_name = _quote_ident(table.name)
                    target_conn.execute(text(f"TRUNCATE TABLE {target_name} RESTART IDENTITY CASCADE"))

            for source_table in source_tables:
                table_name = source_table.name
                target_table = target_meta.tables.get(table_name)
                if target_table is None:
                    print(f"Skipping {table_name}: table missing in target")
                    continue

                source_rows = source_conn.execute(source_table.select()).mappings().all()
                if not source_rows:
                    copied_totals[table_name] = 0
                    print(f"{table_name}: 0 rows")
                    continue

                # Keep only columns that exist in target table.
                target_columns = {column.name for column in target_table.columns}
                prepared_rows: List[Dict] = []
                for row in source_rows:
                    prepared_rows.append(
                        {
                            key: value
                            for key, value in row.items()
                            if key in target_columns
                        }
                    )

                for chunk in _chunk_rows(prepared_rows):
                    target_conn.execute(target_table.insert(), chunk)

                copied_totals[table_name] = len(prepared_rows)
                print(f"{table_name}: copied {len(prepared_rows)} rows")

            # Reset postgres sequences so future inserts don't collide.
            if target_engine.dialect.name.startswith("postgresql"):
                for table_name, copied in copied_totals.items():
                    if copied <= 0:
                        continue
                    target_table = target_meta.tables.get(table_name)
                    if target_table is None:
                        continue

                    pk_columns = list(target_table.primary_key.columns)
                    if len(pk_columns) != 1:
                        continue

                    pk = pk_columns[0]
                    if not getattr(pk.type, "python_type", None) in (int,):
                        continue

                    q_table = _quote_ident(table_name)
                    q_col = _quote_ident(pk.name)
                    seq_sql = f"""
                    SELECT setval(
                        pg_get_serial_sequence('{q_table}', '{pk.name}'),
                        COALESCE((SELECT MAX({q_col}) FROM {q_table}), 1),
                        true
                    )
                    """
                    target_conn.execute(text(seq_sql))

    except SQLAlchemyError as exc:
        raise RuntimeError(f"Migration failed: {exc}") from exc

    print("\nMigration complete.")
    print("Copied totals:")
    for table_name, count in copied_totals.items():
        print(f"- {table_name}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate SQLite data into PostgreSQL/Supabase")
    parser.add_argument(
        "--source-sqlite",
        default=str(_default_source_sqlite()),
        help="Path to source SQLite file (default: Database/s92.db)",
    )
    parser.add_argument(
        "--target-url",
        required=True,
        help="Target PostgreSQL URL (Supabase connection string)",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Truncate target tables before copy",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_sqlite = Path(args.source_sqlite).resolve()
    if not source_sqlite.exists():
        raise FileNotFoundError(f"Source SQLite not found: {source_sqlite}")

    migrate(
        source_sqlite=source_sqlite,
        target_url=args.target_url,
        truncate_target=args.truncate_target,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
