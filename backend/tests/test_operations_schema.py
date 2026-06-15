"""DB-level constraint tests for operation, operation_line, correction (migration 005)."""

from datetime import UTC, date, datetime

import psycopg
import pytest
import pytest_asyncio

from trama import db


@pytest_asyncio.fixture
async def attempt(node_user):
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
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence)
                   VALUES (%s, 'deterministic', 1.0)
                   RETURNING id""",
                (doc_id,),
            )
            (attempt_id,) = await cur.fetchone()
    yield {
        "node_id": node_user["node_id"],
        "doc_id": doc_id,
        "attempt_id": attempt_id,
    }
    # operation has ON DELETE RESTRICT on parse_attempt; clear before node_user
    # cleanup deletes the underlying document.
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM operation WHERE node_id = %s", (node_user["node_id"],)
            )


async def _insert_operation(cur, node_id, attempt_id):
    await cur.execute(
        """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                  operation_date, status, confirmed_at)
           VALUES (%s, %s, 'order', %s, 'confirmed', %s)
           RETURNING id""",
        (node_id, attempt_id, date(2026, 1, 15), datetime.now(UTC)),
    )
    (op_id,) = await cur.fetchone()
    return op_id


@pytest.mark.asyncio
async def test_insert_valid_rows(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            op_id = await _insert_operation(cur, attempt["node_id"], attempt["attempt_id"])
            await cur.execute(
                """INSERT INTO operation_line
                       (operation_id, product, quantity, unit, raw_text, line_no, page)
                   VALUES (%s, 'zanahoria', 3.500, 'kg', 'zanahoria | 3.5 | kg', 1, 1)""",
                (op_id,),
            )
            await cur.execute(
                """INSERT INTO correction
                       (parse_attempt_id, line_no, field, original_value, corrected_value)
                   VALUES (%s, 1, 'product', 'zanaoria', 'zanahoria')""",
                (attempt["attempt_id"],),
            )
            await cur.execute(
                "SELECT COUNT(*) FROM operation_line WHERE operation_id = %s",
                (op_id,),
            )
            (line_count,) = await cur.fetchone()
            await cur.execute(
                "SELECT COUNT(*) FROM correction WHERE parse_attempt_id = %s",
                (attempt["attempt_id"],),
            )
            (corr_count,) = await cur.fetchone()
    assert line_count == 1
    assert corr_count == 1


@pytest.mark.asyncio
async def test_kind_check_rejects_unknown_value(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                              operation_date, status, confirmed_at)
                       VALUES (%s, %s, 'delivery', %s, 'confirmed', %s)""",
                    (
                        attempt["node_id"],
                        attempt["attempt_id"],
                        date(2026, 1, 15),
                        datetime.now(UTC),
                    ),
                )


@pytest.mark.asyncio
async def test_status_check_rejects_unknown_value(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                              operation_date, status, confirmed_at)
                       VALUES (%s, %s, 'order', %s, 'draft', %s)""",
                    (
                        attempt["node_id"],
                        attempt["attempt_id"],
                        date(2026, 1, 15),
                        datetime.now(UTC),
                    ),
                )


@pytest.mark.asyncio
async def test_correction_field_check_rejects_unknown_value(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO correction
                           (parse_attempt_id, line_no, field, original_value)
                       VALUES (%s, 1, 'price', 'x')""",
                    (attempt["attempt_id"],),
                )


@pytest.mark.asyncio
async def test_operation_line_quantity_check_rejects_zero(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            op_id = await _insert_operation(cur, attempt["node_id"], attempt["attempt_id"])
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO operation_line
                           (operation_id, product, quantity, line_no)
                       VALUES (%s, 'zanahoria', 0, 1)""",
                    (op_id,),
                )


@pytest.mark.asyncio
async def test_operation_line_quantity_check_rejects_negative(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            op_id = await _insert_operation(cur, attempt["node_id"], attempt["attempt_id"])
            with pytest.raises(psycopg.errors.CheckViolation):
                await cur.execute(
                    """INSERT INTO operation_line
                           (operation_id, product, quantity, line_no)
                       VALUES (%s, 'zanahoria', -0.5, 1)""",
                    (op_id,),
                )


@pytest.mark.asyncio
async def test_operation_parse_attempt_unique(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await _insert_operation(cur, attempt["node_id"], attempt["attempt_id"])
            with pytest.raises(psycopg.errors.UniqueViolation):
                await cur.execute(
                    """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                              operation_date, status, confirmed_at)
                       VALUES (%s, %s, 'order', %s, 'confirmed', %s)""",
                    (
                        attempt["node_id"],
                        attempt["attempt_id"],
                        date(2026, 1, 16),
                        datetime.now(UTC),
                    ),
                )


@pytest.mark.asyncio
async def test_operation_line_cascade_on_operation_delete(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            op_id = await _insert_operation(cur, attempt["node_id"], attempt["attempt_id"])
            await cur.execute(
                """INSERT INTO operation_line
                       (operation_id, product, quantity, line_no)
                   VALUES (%s, 'zanahoria', 3, 1), (%s, 'tomate', 2, 2)""",
                (op_id, op_id),
            )
            await cur.execute(
                "SELECT COUNT(*) FROM operation_line WHERE operation_id = %s",
                (op_id,),
            )
            (count_before,) = await cur.fetchone()
            await cur.execute("DELETE FROM operation WHERE id = %s", (op_id,))
            await cur.execute(
                "SELECT COUNT(*) FROM operation_line WHERE operation_id = %s",
                (op_id,),
            )
            (count_after,) = await cur.fetchone()
    assert count_before == 2
    assert count_after == 0


@pytest.mark.asyncio
async def test_correction_cascade_on_parse_attempt_delete(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO correction
                       (parse_attempt_id, line_no, field, original_value, corrected_value)
                   VALUES (%s, 1, 'product', 'a', 'b'),
                          (%s, 2, 'quantity', '1', '2')""",
                (attempt["attempt_id"], attempt["attempt_id"]),
            )
            await cur.execute(
                "SELECT COUNT(*) FROM correction WHERE parse_attempt_id = %s",
                (attempt["attempt_id"],),
            )
            (count_before,) = await cur.fetchone()
            await cur.execute(
                "DELETE FROM parse_attempt WHERE id = %s", (attempt["attempt_id"],)
            )
            await cur.execute(
                "SELECT COUNT(*) FROM correction WHERE parse_attempt_id = %s",
                (attempt["attempt_id"],),
            )
            (count_after,) = await cur.fetchone()
    assert count_before == 2
    assert count_after == 0


@pytest.mark.asyncio
async def test_correction_semantics_product_edit(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO correction
                       (parse_attempt_id, line_no, field, original_value, corrected_value)
                   VALUES (%s, 2, 'product', 'tomate', 'tomate cherry')
                   RETURNING line_no, field, original_value, corrected_value""",
                (attempt["attempt_id"],),
            )
            row = await cur.fetchone()
    assert row == (2, "product", "tomate", "tomate cherry")


@pytest.mark.asyncio
async def test_correction_semantics_line_added(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO correction
                       (parse_attempt_id, line_no, field, original_value, corrected_value)
                   VALUES (%s, NULL, 'line_added', NULL,
                           '{"product":"zanahoria","quantity":3}')
                   RETURNING line_no, field, original_value, corrected_value""",
                (attempt["attempt_id"],),
            )
            row = await cur.fetchone()
    assert row == (None, "line_added", None, '{"product":"zanahoria","quantity":3}')


@pytest.mark.asyncio
async def test_correction_semantics_line_removed(attempt):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO correction
                       (parse_attempt_id, line_no, field, original_value, corrected_value)
                   VALUES (%s, 5, 'line_removed',
                           '{"product":"basura","quantity":1}', NULL)
                   RETURNING line_no, field, original_value, corrected_value""",
                (attempt["attempt_id"],),
            )
            row = await cur.fetchone()
    assert row == (5, "line_removed", '{"product":"basura","quantity":1}', None)
