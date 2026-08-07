"""
migrate.py
----------
Database migration script for EasyGov Nepal.

Run this once (or whenever you add a new table/column) to create all
SQLAlchemy-defined tables in the database.

Usage (from project root):
    python app/migrate.py

This script is IDEMPOTENT — it uses SQLAlchemy's create_all() which only
creates tables that don't already exist, so it is safe to run multiple times.
"""

import sys
import os

# ── PATH SETUP ────────────────────────────────────────────────────────────────
# Ensure 'app' package is importable when running from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, DATABASE_URL

# Import all models so that Base.metadata knows about all tables.
# If you add a new model to models.py, make sure it's imported here.
from app.models import User, GovService, PrerequisiteRule, UserService, Progress, ChatMessage  # noqa: F401


def run_migrations():
    print("=" * 60)
    print("  EasyGov Nepal — Database Migration")
    print("=" * 60)
    print(f"\n[DB]   Target database  : {DATABASE_URL}")
    print(f"[INFO] Tables to create : {', '.join(Base.metadata.tables.keys())}")
    print()

    # Ensure the db_storage directory exists
    os.makedirs("db_storage", exist_ok=True)

    try:
        # create_all() creates tables that do not yet exist.
        # It will NOT drop or alter existing tables (no destructive changes).
        Base.metadata.create_all(bind=engine)

        print("[OK] Migration complete! Tables created successfully:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)

    print("\n[NEXT] Run 'python app/seed_data.py' to populate initial data.")
    print("=" * 60)


if __name__ == "__main__":
    run_migrations()
