"""
One-time script to initialize all database tables.
Run this once: python setup_db.py
"""

from ingestion.database import init_schema

if __name__ == "__main__":
    print("Initializing database schema...")
    init_schema()
    print("✅ All tables created successfully")
