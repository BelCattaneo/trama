import os
import sys

import psycopg

from trama.config import settings

PRODUCER = {
    "cuit": "20-12345678-6",
    "display_name": "Productor Demo",
    "role": "producer",
    "latitude": -34.61,
    "longitude": -58.38,
    "zone_label": "Buenos Aires",
}


def seed() -> None:
    if os.getenv("ENV") != "dev":
        print("seed_dev requires ENV=dev", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO node (cuit, display_name, role, latitude, longitude, zone_label)
                VALUES (%(cuit)s, %(display_name)s, %(role)s,
                        %(latitude)s, %(longitude)s, %(zone_label)s)
                ON CONFLICT (cuit) DO NOTHING
                RETURNING id
                """,
                PRODUCER,
            )
            row = cur.fetchone()
        conn.commit()

    if row:
        print(f"inserted producer node {row[0]}")
    else:
        print("producer node already exists")


if __name__ == "__main__":
    seed()
