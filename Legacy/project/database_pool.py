"""
Shared PostgreSQL connection pool.
"""

from __future__ import annotations

import logging
from threading import Lock

from psycopg2.pool import ThreadedConnectionPool

from config import DB_CONFIG, DB_POOL_MAX_CONN, DB_POOL_MIN_CONN

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = Lock()


class PooledConnection:
    def __init__(self, pool: ThreadedConnectionPool, conn):
        self._pool = pool
        self._conn = conn
        self._released = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if not self._released:
            self._pool.putconn(self._conn)
            self._released = True

    def really_close(self):
        if not self._released:
            self._pool.putconn(self._conn, close=True)
            self._released = True


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(
                    DB_POOL_MIN_CONN,
                    DB_POOL_MAX_CONN,
                    **DB_CONFIG,
                )
                logger.info(
                    "Initialized DB connection pool (%s-%s)",
                    DB_POOL_MIN_CONN,
                    DB_POOL_MAX_CONN,
                )
    return _pool


def get_connection():
    pool = get_pool()
    conn = pool.getconn()
    return PooledConnection(pool, conn)
