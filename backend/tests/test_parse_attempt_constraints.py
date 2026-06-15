"""DB-level constraint tests for the parse_attempt table (migration 004)."""

import json

import psycopg
import pytest
import pytest_asyncio

from trama import db


@pytest_asyncio.fixture
async def doc(node_user):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, 'fix.xlsx',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           100, %s, 'ab/dummy')
                   RETURNING id""",
                (node_user["node_id"], "f" * 64),
            )
            (doc_id,) = await cur.fetchone()
    yield {"node_id": node_user["node_id"], "doc_id": doc_id}


@pytest.mark.asyncio
async def test_strategy_check_rejects_unknown_value(doc):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO parse_attempt (document_id, strategy)
                       VALUES (%s, 'manual')""",
                    (doc["doc_id"],),
                )


@pytest.mark.asyncio
async def test_confidence_check_rejects_above_one(doc):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO parse_attempt (document_id, strategy, confidence)
                       VALUES (%s, 'deterministic', 1.5)""",
                    (doc["doc_id"],),
                )


@pytest.mark.asyncio
async def test_confidence_check_rejects_below_zero(doc):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO parse_attempt (document_id, strategy, confidence)
                       VALUES (%s, 'deterministic', -0.1)""",
                    (doc["doc_id"],),
                )


@pytest.mark.asyncio
async def test_confidence_allows_null(doc):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence)
                   VALUES (%s, 'deterministic', NULL)
                   RETURNING id""",
                (doc["doc_id"],),
            )
            (attempt_id,) = await cur.fetchone()
    assert attempt_id is not None


@pytest.mark.asyncio
async def test_winner_partial_unique_index_rejects_second_winner(doc):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                              is_winner)
                   VALUES (%s, 'deterministic', 1.0, TRUE)""",
                (doc["doc_id"],),
            )
            with pytest.raises(psycopg.errors.UniqueViolation):
                await cur.execute(
                    """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                                  is_winner)
                       VALUES (%s, 'llm', 0.9, TRUE)""",
                    (doc["doc_id"],),
                )


@pytest.mark.asyncio
async def test_multiple_non_winner_attempts_allowed(doc):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence)
                   VALUES (%s, 'deterministic', 1.0), (%s, 'llm', 0.9)""",
                (doc["doc_id"], doc["doc_id"]),
            )
            await cur.execute(
                "SELECT COUNT(*) FROM parse_attempt WHERE document_id = %s",
                (doc["doc_id"],),
            )
            (count,) = await cur.fetchone()
    assert count == 2


@pytest.mark.asyncio
async def test_cascade_on_document_delete(doc):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence)
                   VALUES (%s, 'deterministic', 1.0), (%s, 'llm', 0.9)""",
                (doc["doc_id"], doc["doc_id"]),
            )
            await cur.execute(
                "SELECT COUNT(*) FROM parse_attempt WHERE document_id = %s",
                (doc["doc_id"],),
            )
            (count_before,) = await cur.fetchone()
            await cur.execute(
                "DELETE FROM document WHERE id = %s", (doc["doc_id"],)
            )
            await cur.execute(
                "SELECT COUNT(*) FROM parse_attempt WHERE document_id = %s",
                (doc["doc_id"],),
            )
            (count_after,) = await cur.fetchone()
    assert count_before == 2
    assert count_after == 0


@pytest.mark.asyncio
async def test_winner_can_swap(doc):
    """Setting one winner false and a different row true succeeds."""
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                              is_winner)
                   VALUES (%s, 'deterministic', 1.0, TRUE),
                          (%s, 'llm', 0.9, FALSE)
                   RETURNING id, strategy""",
                (doc["doc_id"], doc["doc_id"]),
            )
            rows = await cur.fetchall()
            deterministic_id = next(r[0] for r in rows if r[1] == "deterministic")
            llm_id = next(r[0] for r in rows if r[1] == "llm")
            await cur.execute(
                "UPDATE parse_attempt SET is_winner = FALSE WHERE id = %s",
                (deterministic_id,),
            )
            await cur.execute(
                "UPDATE parse_attempt SET is_winner = TRUE WHERE id = %s",
                (llm_id,),
            )
            await cur.execute(
                """SELECT strategy FROM parse_attempt
                   WHERE document_id = %s AND is_winner""",
                (doc["doc_id"],),
            )
            row = await cur.fetchone()
    assert row[0] == "llm"


@pytest.mark.asyncio
async def test_payload_jsonb_round_trips(doc):
    payload = {"lines": [{"product": "x", "quantity": 1.5}], "warnings": []}
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                              payload)
                   VALUES (%s, 'deterministic', 1.0, %s::jsonb)
                   RETURNING payload""",
                (doc["doc_id"], json.dumps(payload)),
            )
            (stored,) = await cur.fetchone()
    assert stored == payload
