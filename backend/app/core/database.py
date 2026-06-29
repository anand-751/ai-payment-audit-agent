import sqlite3
from pathlib import Path

from app.config import settings


def _resolve_db_path() -> str:
    """
    Resolve the SQLite database path from settings.DB_PATH.

    Prints the resolved path once during application startup so it's
    immediately obvious which SQLite database the backend is using.
    """

    db_path = Path(settings.DB_PATH).expanduser().resolve()

    # Ensure the parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return str(db_path)


# Single resolved database path used everywhere
DB_PATH = _resolve_db_path()

print(f">>> USING SQLITE DB: {DB_PATH} <<<")


def get_db_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite connection.

    This is the single source of truth for the database path.

    Every backend module (authentication, uploads, audit engine,
    CFO dashboard, approvals, history, notifications, etc.)
    should obtain its connection through this function.

    Railway:
        Set DB_PATH to the mounted persistent volume, e.g.

        DB_PATH=/data/payment_audit.seed.db
    """

    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    # SQLite concurrency improvements
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


def get_db():
    """
    FastAPI dependency.

    Usage:

        @router.get(...)
        def endpoint(db=Depends(get_db)):
            ...

    Automatically closes the connection after the request.
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