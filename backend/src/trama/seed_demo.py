"""Seed the cooperative network demo dataset from backend/seeds/network.json."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import psycopg

from trama.config import settings

SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"
NETWORK_JSON = SEEDS_DIR / "network.json"


def load_network(path: Path = NETWORK_JSON) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _insert_nodes(cur, nodes: list[dict], dry_run: bool) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    for node in nodes:
        cur.execute("SELECT id FROM node WHERE cuit = %s", (node["cuit"],))
        existing = cur.fetchone()
        if existing is not None:
            skipped += 1
            continue
        if dry_run:
            inserted += 1
            continue
        cur.execute(
            """INSERT INTO node (cuit, display_name, role, address_text,
                                 latitude, longitude, zone_label)
               VALUES (%(cuit)s, %(display_name)s, %(role)s, %(address_text)s,
                       %(latitude)s, %(longitude)s, %(zone_label)s)""",
            node,
        )
        inserted += 1
    return inserted, skipped


def _node_id_by_cuit(cur, cuit: str) -> str | None:
    cur.execute("SELECT id FROM node WHERE cuit = %s", (cuit,))
    row = cur.fetchone()
    return row[0] if row else None


def _seed_op_hash(op: dict) -> str:
    """Stable content_hash for a seed operation, used as the idempotency key."""
    canonical = json.dumps(
        {
            "buyer": op["buyer_cuit"],
            "supplier": op["supplier_cuit"],
            "days_ago": op["days_ago"],
            "products": op["products"],
        },
        sort_keys=True,
    )
    return "seed-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:59]


def _insert_operations(
    cur, operations: list[dict], dry_run: bool, known_cuits: set[str] | None = None
) -> tuple[int, int]:
    """Insert demo operations. Idempotent via document.content_hash."""
    inserted = 0
    skipped = 0
    for op in operations:
        buyer_id = _node_id_by_cuit(cur, op["buyer_cuit"])
        supplier_id = _node_id_by_cuit(cur, op["supplier_cuit"])
        if buyer_id is None or supplier_id is None:
            if dry_run and known_cuits is not None:
                if op["buyer_cuit"] in known_cuits and op["supplier_cuit"] in known_cuits:
                    inserted += 1
                    continue
            skipped += 1
            continue
        op_hash = _seed_op_hash(op)
        cur.execute("SELECT 1 FROM document WHERE content_hash = %s", (op_hash,))
        if cur.fetchone() is not None:
            skipped += 1
            continue
        if dry_run:
            inserted += 1
            continue
        cur.execute(
            """INSERT INTO document (node_id, original_filename, mime_type,
                                     size_bytes, content_hash, storage_ref)
               VALUES (%s, 'seed.csv', 'text/csv', 1, %s, 'seed/x')
               RETURNING id""",
            (buyer_id, op_hash),
        )
        (doc_id,) = cur.fetchone()
        cur.execute(
            """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                          payload, is_winner)
               VALUES (%s, 'deterministic', 1.0, NULL, true)
               RETURNING id""",
            (doc_id,),
        )
        (attempt_id,) = cur.fetchone()
        cur.execute(
            """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                      operation_date, status, supplier_node_id,
                                      confirmed_at)
               VALUES (%s, %s, 'order', current_date, 'confirmed', %s,
                       now() - (%s || ' days')::interval)
               RETURNING id""",
            (buyer_id, attempt_id, supplier_id, op["days_ago"]),
        )
        (operation_id,) = cur.fetchone()
        for idx, product in enumerate(op["products"], start=1):
            cur.execute(
                """INSERT INTO operation_line
                       (operation_id, product, quantity, unit, line_no)
                   VALUES (%s, %s, 1.0, 'kg', %s)""",
                (operation_id, product, idx),
            )
        inserted += 1
    return inserted, skipped


def _wipe_seed(cur, network: dict) -> int:
    cuits = [n["cuit"] for n in network["nodes"]]
    cur.execute(
        """DELETE FROM operation
           WHERE node_id IN (SELECT id FROM node WHERE cuit = ANY(%s))
              OR supplier_node_id IN (SELECT id FROM node WHERE cuit = ANY(%s))""",
        (cuits, cuits),
    )
    cur.execute(
        """DELETE FROM document
           WHERE node_id IN (SELECT id FROM node WHERE cuit = ANY(%s))
             AND storage_ref = 'seed/x'""",
        (cuits,),
    )
    cur.execute(
        """DELETE FROM node
           WHERE cuit = ANY(%s)
             AND NOT EXISTS (SELECT 1 FROM app_user WHERE node_id = node.id)""",
        (cuits,),
    )
    return cur.rowcount


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed the cooperative network demo dataset.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be inserted without touching the database.",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Delete all seed-owned nodes (no app_user linked) and their operations first.",
    )
    args = parser.parse_args(argv)

    network = load_network()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            if args.wipe:
                wiped = _wipe_seed(cur, network)
                print(f"wiped {wiped} seed nodes")
            n_inserted, n_skipped = _insert_nodes(cur, network["nodes"], args.dry_run)
            known_cuits = {n["cuit"] for n in network["nodes"]}
            o_inserted, o_skipped = _insert_operations(
                cur, network["operations"], args.dry_run, known_cuits=known_cuits
            )
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()

    label = "would insert" if args.dry_run else "inserted"
    print(f"{label} {n_inserted} nodes, skipped {n_skipped}")
    print(f"{label} {o_inserted} operations, skipped {o_skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
