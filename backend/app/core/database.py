import sqlite3

from app.config import settings


def get_db_connection():
    """
    Single source of truth for the DB path.
    ALWAYS uses settings.DB_PATH so every module (auth, upload, batches,
    approval, decision) reads/writes the SAME database file -- including the
    Railway volume path when DB_PATH is set as an env var in production.
    """
    conn = sqlite3.connect(
        settings.DB_PATH,
        timeout=30,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    # SQLite concurrency improvements
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")

    return conn


def get_db():
    """
    FastAPI dependency used by routes that do `Depends(get_db)`
    (e.g. approval.py). Yields a connection and always closes it.
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()




# import sqlite3
# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent

# DATABASE_PATH = BASE_DIR / "db" / "payment_audit.db"


# def get_db_connection():

#     conn = sqlite3.connect(
#         DATABASE_PATH,
#         timeout=30,
#         check_same_thread=False
#     )

#     conn.row_factory = sqlite3.Row

#     # SQLite concurrency improvements
#     conn.execute("PRAGMA journal_mode=WAL;")
#     conn.execute("PRAGMA busy_timeout=30000;")

#     return conn