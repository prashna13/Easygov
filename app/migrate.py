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

from sqlalchemy import inspect, text

from app.database import engine, Base, DATABASE_URL

# Import all models so that Base.metadata knows about all tables.
# If you add a new model to models.py, make sure it's imported here.
from app.models import User, GovService, PrerequisiteRule, UserService, Progress, ChatMessage, Document  # noqa: F401

# Columns that were added AFTER the original table creation.
# create_all() does NOT add columns to existing tables, so we patch them here.
# Format: { table_name: { column_name: "COLUMN_DEFINITION" } }
ADD_COLUMNS = {
    "users": {
        "age":                "INTEGER",
        "onboarding_completed": "BOOLEAN DEFAULT 0 NOT NULL",
    },
    "gov_services": {
        "guidance":        "TEXT",
        "title_ne":        "VARCHAR(200)",
        "category_ne":     "VARCHAR(100)",
        "description_ne":  "TEXT",
        "guidance_ne":     "TEXT",
    },
    "progress": {
        "step_name_ne":         "VARCHAR(200)",
        "step_description_ne":  "TEXT",
    },
}


def _apply_column_additions():
    """ALTER TABLE ... ADD COLUMN for columns missing from existing tables."""
    inspector = inspect(engine)
    for table_name, columns in ADD_COLUMNS.items():
        if table_name not in inspector.get_table_names():
            continue
        existing = {col["name"] for col in inspector.get_columns(table_name)}
        for col_name, col_def in columns.items():
            if col_name in existing:
                continue
            print(f"[MIGRATE] Adding column {table_name}.{col_name}")
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"))


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

        # Patch existing tables with any newly-added columns
        _apply_column_additions()

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
