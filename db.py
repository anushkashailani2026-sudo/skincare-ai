"""
Database management module for Skincare AI.
Supports both SQLite (local development) and PostgreSQL (production / Render).
Ensures safe schema migrations and data preservation.
"""

import os
import sqlite3
import bcrypt
from datetime import datetime
from contextlib import contextmanager

FEEDBACK_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "feedback.db")


def get_database_url():
    """Retrieve and normalize database connection string from environment."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def is_postgres():
    return bool(get_database_url())


@contextmanager
def get_db_connection():
    """Context manager for database connections (SQLite or PostgreSQL)."""
    db_url = get_database_url()
    if db_url:
        import psycopg
        conn = psycopg.connect(db_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        os.makedirs(os.path.dirname(FEEDBACK_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(FEEDBACK_DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def execute_query(query, params=None, fetchone=False, fetchall=False):
    """
    Execute a parameterized SQL query with automatic placeholder translation:
    Use '?' in query strings; it automatically converts to '%s' for PostgreSQL.
    """
    if params is None:
        params = []

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if is_postgres():
                pg_query = query.replace("?", "%s")
                cursor.execute(pg_query, params)
            else:
                cursor.execute(query, params)

            if fetchone:
                row = cursor.fetchone()
                if row is not None and not isinstance(row, dict):
                    cols = [desc[0] for desc in cursor.description]
                    return dict(zip(cols, row))
                return row

            if fetchall:
                rows = cursor.fetchall()
                if rows and not isinstance(rows[0], dict):
                    cols = [desc[0] for desc in cursor.description]
                    return [dict(zip(cols, r)) for r in rows]
                return [dict(r) for r in rows] if rows else []

            # If insert / update / delete, return lastrowid or rowcount
            last_id = getattr(cursor, "lastrowid", None)
            row_count = getattr(cursor, "rowcount", None)
            return last_id if last_id is not None else row_count
        finally:
            cursor.close()


def init_db():
    """Initialize all persistent database tables if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        pg = is_postgres()

        id_serial = "BIGSERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        id_int_serial = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        ts_type = "TIMESTAMPTZ" if pg else "TEXT"

        # 1. Existing skincare_feedback table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS skincare_feedback (
                id {id_serial},
                rating INTEGER CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5)),
                category TEXT NOT NULL DEFAULT 'general',
                message TEXT NOT NULL,
                user_name TEXT DEFAULT '',
                user_email TEXT DEFAULT '',
                created_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Auto-migrate columns if missing
        if pg:
            cursor.execute("ALTER TABLE skincare_feedback ADD COLUMN IF NOT EXISTS user_name TEXT DEFAULT '';")
            cursor.execute("ALTER TABLE skincare_feedback ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT '';")
        else:
            cursor.execute("PRAGMA table_info(skincare_feedback)")
            cols = [c[1] for c in cursor.fetchall()]
            if 'user_name' not in cols:
                cursor.execute("ALTER TABLE skincare_feedback ADD COLUMN user_name TEXT DEFAULT ''")
            if 'user_email' not in cols:
                cursor.execute("ALTER TABLE skincare_feedback ADD COLUMN user_email TEXT DEFAULT ''")

        # 2. Existing skincare_admin table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS skincare_admin (
                id {id_int_serial},
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed initial admin if none exists
        cursor.execute("SELECT COUNT(*) FROM skincare_admin")
        admin_count = cursor.fetchone()[0]
        if admin_count == 0:
            admin_id = os.getenv("ADMIN_ID") or os.getenv("ADMIN_USERNAME") or "admin"
            admin_pw = os.getenv("ADMIN_PASSWORD") or "admin123"
            pw_hash = bcrypt.hashpw(admin_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            if pg:
                cursor.execute(
                    "INSERT INTO skincare_admin (username, password_hash) VALUES (%s, %s)",
                    (admin_id, pw_hash)
                )
            else:
                cursor.execute(
                    "INSERT INTO skincare_admin (username, password_hash) VALUES (?, ?)",
                    (admin_id, pw_hash)
                )

        # 3. Users table (for User Registration & Login)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {id_serial},
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                skin_type TEXT DEFAULT '',
                created_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Products table (Persistent External Product Catalogue)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                category TEXT NOT NULL,
                barcode TEXT DEFAULT '',
                product_size TEXT DEFAULT '',
                ingredients_text TEXT DEFAULT '',
                description TEXT DEFAULT '',
                skin_types TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                source_url TEXT DEFAULT '',
                source_provider TEXT DEFAULT 'Open Beauty Facts',
                source_product_id TEXT DEFAULT '',
                country TEXT DEFAULT 'India',
                price_inr REAL DEFAULT NULL,
                rating REAL DEFAULT NULL,
                review_count INTEGER DEFAULT 0,
                completeness_score INTEGER DEFAULT 0,
                last_updated {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_verified {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. User Reviews table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_reviews (
                id {id_serial},
                user_id BIGINT NOT NULL,
                user_name TEXT NOT NULL,
                user_email TEXT DEFAULT '',
                product_id TEXT DEFAULT '',
                product_name TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                title TEXT NOT NULL,
                review_text TEXT NOT NULL,
                skin_type TEXT DEFAULT '',
                skin_concern TEXT DEFAULT '',
                duration_used TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'approved',
                admin_seen INTEGER NOT NULL DEFAULT 0,
                created_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. External Reviews table (Provider architecture for verified 3rd-party review feeds)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS external_reviews (
                id {id_serial},
                product_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT DEFAULT '',
                avg_rating REAL DEFAULT NULL,
                total_reviews INTEGER DEFAULT 0,
                positive_themes TEXT DEFAULT '',
                negative_themes TEXT DEFAULT '',
                sample_reviews_json TEXT DEFAULT '[]',
                last_fetched {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 7. Product Prices table (Multi-retailer price comparison)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS product_prices (
                id {id_serial},
                product_id TEXT NOT NULL,
                retailer TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                product_size TEXT DEFAULT '',
                price_per_unit TEXT DEFAULT '',
                product_url TEXT DEFAULT '',
                in_stock INTEGER NOT NULL DEFAULT 1,
                last_retrieved {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. User Skin Profiles table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id BIGINT PRIMARY KEY,
                skin_type TEXT DEFAULT 'combination',
                skin_concerns TEXT DEFAULT '',
                skin_concern TEXT DEFAULT '',
                sensitivities TEXT DEFAULT '',
                budget_preference TEXT DEFAULT 'medium',
                am_routine_pref TEXT DEFAULT '',
                pm_routine_pref TEXT DEFAULT '',
                updated_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        if pg:
            cursor.execute("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS skin_concern TEXT DEFAULT '';")
        else:
            cursor.execute("PRAGMA table_info(user_profiles)")
            p_cols = [c[1] for c in cursor.fetchall()]
            if 'skin_concern' not in p_cols:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN skin_concern TEXT DEFAULT ''")

        # 9. Skincare Routines table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS skincare_routines (
                id {id_serial},
                user_id BIGINT NOT NULL,
                routine_name TEXT NOT NULL,
                routine_type TEXT NOT NULL CHECK (routine_type IN ('am', 'pm', 'custom')),
                description TEXT DEFAULT '',
                created_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 10. Routine Items table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS routine_items (
                id {id_serial},
                routine_id BIGINT NOT NULL,
                step_order INTEGER NOT NULL,
                step_category TEXT NOT NULL,
                product_id TEXT DEFAULT '',
                product_name TEXT NOT NULL,
                usage_notes TEXT DEFAULT ''
            )
        """)

        # 11. Skincare Journal table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS skincare_journal (
                id {id_serial},
                user_id BIGINT NOT NULL,
                entry_date TEXT NOT NULL,
                products_used TEXT DEFAULT '',
                skin_feeling TEXT DEFAULT '',
                observations TEXT DEFAULT '',
                irritation_experienced INTEGER NOT NULL DEFAULT 0,
                irritation_notes TEXT DEFAULT '',
                daily_rating INTEGER NOT NULL DEFAULT 5,
                created_at {ts_type} NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.close()
