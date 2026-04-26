"""
Centralized database configuration.

All modules should import from here instead of hardcoding credentials.
Reads from environment variables with fallback defaults.
"""

import os

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "regtech"),
    "user": os.getenv("DB_USER", "nishank"),
    "password": os.getenv("DB_PASSWORD", "1234"),
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
}

DB_POOL_MIN_CONN = int(os.getenv("DB_POOL_MIN_CONN", "1"))
DB_POOL_MAX_CONN = int(os.getenv("DB_POOL_MAX_CONN", "10"))
