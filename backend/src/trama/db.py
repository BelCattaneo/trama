from psycopg_pool import AsyncConnectionPool

pool: AsyncConnectionPool | None = None


async def open_pool(database_url: str, min_size: int, max_size: int) -> None:
    global pool
    pool = AsyncConnectionPool(
        database_url, min_size=min_size, max_size=max_size, open=False
    )
    await pool.open()


async def close_pool() -> None:
    global pool
    if pool is None:
        return
    await pool.close()
    pool = None


async def db_ok() -> bool:
    if pool is None:
        return False
    try:
        async with pool.connection(timeout=2) as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False
