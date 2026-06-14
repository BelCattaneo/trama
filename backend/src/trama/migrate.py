import argparse
from pathlib import Path

import psycopg

from trama.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS _migration (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def list_migrations() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def applied_versions(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM _migration")
        return {row[0] for row in cur.fetchall()}


def up(dry_run: bool) -> None:
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()

        applied = applied_versions(conn)
        pending = [m for m in list_migrations() if m.stem not in applied]

        if not pending:
            print("no pending migrations")
            return

        for m in pending:
            if dry_run:
                print(f"would apply {m.stem}")
                continue
            with conn.cursor() as cur:
                cur.execute(m.read_text())
                cur.execute(
                    "INSERT INTO _migration (version) VALUES (%s)", (m.stem,)
                )
            conn.commit()
            print(f"applied {m.stem}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="trama.migrate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    up_parser = sub.add_parser("up", help="apply pending migrations")
    up_parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.cmd == "up":
        up(args.dry_run)


if __name__ == "__main__":
    main()
