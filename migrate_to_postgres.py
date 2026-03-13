"""
migrate_to_postgres.py — Migrate data from SQLite to PostgreSQL.

Usage:
  python migrate_to_postgres.py [--pg-url postgresql://user:pass@host:5432/dbname]

If --pg-url is not provided, uses DATABASE_URL environment variable
or defaults to: postgresql://auditoria:auditoria_secret_2026@localhost:5432/auditoria_ta
"""

import sqlite3
import os
import sys
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def migrate(sqlite_path: str, pg_url: str):
    """Copy all data from SQLite to PostgreSQL."""
    import psycopg2

    print(f"Source: {sqlite_path}")
    print(f"Target: {pg_url.split('@')[-1] if '@' in pg_url else pg_url}")
    print()

    if not Path(sqlite_path).exists():
        print(f"Error: SQLite file not found: {sqlite_path}")
        sys.exit(1)

    # Connect SQLite
    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row

    # Connect PostgreSQL
    pg = psycopg2.connect(pg_url)
    cur = pg.cursor()

    # Init PG tables
    print("Creating PostgreSQL tables...")
    os.environ["DATABASE_URL"] = pg_url
    from backend.db import _init_postgres
    _init_postgres()

    # Tables to migrate (order matters for FK constraints)
    tables = [
        "auditorias",
        "avaliacoes",
        "audit_log",
        "chat_revisao",
        "diario_auditoria",
        "aprendizados",
        "snapshots_nota",
        "users",
    ]

    for table in tables:
        try:
            # Check if table exists in SQLite
            try:
                sq_cursor = sq.execute(f"SELECT * FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                print(f"  Info: Table '{table}' not found in SQLite — skipping")
                continue

            rows = sq.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"  Empty {table}: 0 rows — skipping")
                continue

            # Get source columns
            source_columns = [desc[0] for desc in sq_cursor.description]
            
            # Get target columns from PG
            cur.execute(f"SELECT * FROM {table} LIMIT 0")
            target_columns = [desc[0] for desc in cur.description]
            
            # Common columns
            common_columns = [c for c in source_columns if c in target_columns]
            
            if not common_columns:
                print(f"  Warning: No common columns for '{table}' — skipping")
                continue

            # Clear existing data in PG
            cur.execute(f"DELETE FROM {table}")

            cols_str = ", ".join(common_columns)
            placeholders = ", ".join(["%s"] * len(common_columns))

            # Insert rows
            count = 0
            for row in rows:
                values = [row[c] for c in common_columns]
                # Handle NaN floats
                values = [None if isinstance(v, float) and v != v else v for v in values]
                
                try:
                    cur.execute(f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})", values)
                    count += 1
                except Exception as e:
                    print(f"    Error in {table} row: {e}")
                    continue

            # Reset sequence
            if "id" in target_columns:
                try:
                    cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {table}")
                except: pass

            pg.commit()
            print(f"  Done {table}: {count} rows migrated")

        except Exception as e:
            pg.rollback()
            print(f"  Fatal error migrating '{table}': {e}")
            continue

    pg.close()
    sq.close()
    print()
    print("Migration complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument("--sqlite", default=r"C:\AuditoriaTA\dados\auditoria_ta.db",
                       help="Path to SQLite database file")
    parser.add_argument("--pg-url",
                       default=os.environ.get("DATABASE_URL",
                           "postgresql://auditoria:auditoria_secret_2026@localhost:5432/auditoria_ta"),
                       help="PostgreSQL connection URL")
    args = parser.parse_args()

    migrate(args.sqlite, args.pg_url)
