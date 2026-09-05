import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "app.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        avatar_filename TEXT DEFAULT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        original_filename TEXT NOT NULL,
        generated_filename TEXT NOT NULL,
        topic_count INTEGER DEFAULT 0,
        page_count INTEGER DEFAULT 0,
        topics_preview TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    # Safe migration: add column if it doesn't exist yet (for existing databases)
    existing_cols = [
        row[1] for row in conn.execute("PRAGMA table_info(users)")
    ]
    if "avatar_filename" not in existing_cols:
        conn.execute("ALTER TABLE users ADD COLUMN avatar_filename TEXT DEFAULT NULL")
        conn.commit()

    conn.close()
