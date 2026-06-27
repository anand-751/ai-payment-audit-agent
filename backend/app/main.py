from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth_routes import router as auth_router
from app.routes.websocket_routes import router as websocket_router
from app.api.routes.upload import (
    router as upload_router
)
from app.api.routes.audit import (
    router as audit_router
)
from app.api.routes.email import (
    router as email_router
)
from app.api.routes.decision import (
    router as decision_router
)

# DB bootstrap dependencies. These imports already work elsewhere in the app,
# so init runs reliably regardless of whether app/db is a package.
import os
import shutil
from pathlib import Path
from app.config import settings
from app.core.database import get_db_connection

print("MAIN.PY LOADED")


# ---------------------------------------------------------------------------
# INLINE DATABASE INITIALIZER
# Creates every table/column/index, seeds users, and loads reference data on
# startup. Idempotent and safe to run on every boot. Inlined here (instead of
# importing app.db.init_db) so a missing/!package app/db folder can never crash
# startup again.
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS payment_batches (
    batch_id TEXT PRIMARY KEY,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_items INTEGER,
    total_amount REAL,
    batch_status TEXT,
    file_path TEXT,
    cfo_comment TEXT
);

CREATE TABLE IF NOT EXISTS payment_items (
    payment_id TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    amount REAL NOT NULL,
    bank_routing TEXT,
    authorizer TEXT,
    due_date TEXT,
    invoice_date TEXT,
    early_pay_discount REAL,
    early_pay_deadline TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (batch_id, payment_id),
    FOREIGN KEY (batch_id) REFERENCES payment_batches(batch_id)
);

CREATE TABLE IF NOT EXISTS payment_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_date TEXT,
    status TEXT,
    bank_routing_used TEXT
);

CREATE TABLE IF NOT EXISTS vendor_master (
    vendor_id TEXT PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    gl_account_code TEXT,
    approved_bank_routing TEXT,
    payment_terms TEXT,
    is_active BOOLEAN
);

CREATE TABLE IF NOT EXISTS invoice_register (
    payment_id TEXT PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    approved_invoice_amount REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_results (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    payment_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    violation_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS batch_decision_history (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    file_name TEXT,
    decision TEXT,
    decided_by TEXT,
    decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comment TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT,
    recipient_role TEXT,
    notification_type TEXT,
    title TEXT,
    message TEXT,
    decision TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT,
    full_name TEXT
);

CREATE INDEX IF NOT EXISTS idx_history_invoice ON payment_history(invoice_number);
CREATE INDEX IF NOT EXISTS idx_vendor_id ON vendor_master(vendor_id);
CREATE INDEX IF NOT EXISTS idx_payment_vendor ON payment_items(vendor_id);
CREATE INDEX IF NOT EXISTS idx_batch_id ON payment_items(batch_id);
"""

REFERENCE_TABLES = ("vendor_master", "invoice_register", "payment_history")


def _ensure_column(cur, table, column, ddl_type):
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def _find_seed():
    """Locate the committed seed DB if it shipped in the image. Best-effort."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "db" / "payment_audit.seed.db",
        here / "db" / "payment_audit.db",
        Path("/app/app/db/payment_audit.seed.db"),
        Path("/app/app/db/payment_audit.db"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _seed_reference_data(conn, cur):
    """Populate vendor_master / invoice_register / payment_history if empty.

    Works on an already-created (empty) volume DB. Prefers a committed
    seed_reference.sql text file (cannot be gitignored by *.db rules); falls
    back to copying from a shipped seed .db via ATTACH.
    """
    force = os.environ.get("RESEED_REFERENCE", "").strip().lower() in (
        "1", "true", "yes",
    )
    cur.execute("SELECT COUNT(*) FROM vendor_master")
    if cur.fetchone()[0] > 0 and not force:
        print("REFERENCE DATA ALREADY PRESENT")
        return
    if force:
        print("RESEED_REFERENCE set -- wiping and reloading reference data")

    # --- Option A: replay committed SQL dump (most reliable) ---
    sql_file = Path(__file__).resolve().parent / "seed_reference.sql"
    if sql_file.exists():
        cur.executescript(sql_file.read_text())
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM vendor_master")
        v = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM invoice_register")
        i = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payment_history")
        h = cur.fetchone()[0]
        print(
            "REFERENCE DATA LOADED FROM seed_reference.sql "
            f"(vendors={v}, invoices={i}, history={h})"
        )
        return

    # --- Option B: copy from a shipped seed .db via ATTACH ---
    seed = _find_seed()
    if seed is not None:
        conn.commit()  # ATTACH cannot run inside a transaction
        cur.execute("ATTACH DATABASE ? AS seed", (str(seed),))
        for tbl in REFERENCE_TABLES:
            cur.execute(f"INSERT INTO {tbl} SELECT * FROM seed.{tbl}")
        conn.commit()
        cur.execute("DETACH DATABASE seed")
        print(f"REFERENCE DATA LOADED FROM {seed} via ATTACH")
        return

    print(
        "WARNING: no reference data source found "
        "(seed_reference.sql / seed .db both missing); vendor_master is EMPTY "
        "-- every payment will flag INVALID_VENDOR."
    )


def init_db():
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # First boot on an empty volume: copy a committed seed .db whole if present.
    seed = _find_seed()
    if (
        not db_path.exists()
        and seed is not None
        and db_path.resolve() != seed.resolve()
    ):
        shutil.copy(seed, db_path)
        print(f"SEED DB COPIED FROM {seed}")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.executescript(SCHEMA_SQL)

    _ensure_column(cur, "payment_batches", "file_path", "TEXT")
    _ensure_column(cur, "payment_batches", "cfo_comment", "TEXT")
    _ensure_column(cur, "payment_batches", "audit_json", "TEXT")
    _ensure_column(cur, "payment_batches", "file_name", "TEXT")
    _ensure_column(cur, "payment_batches", "uploaded_by", "TEXT")
    _ensure_column(cur, "payment_batches", "uploaded_by_name", "TEXT")
    _ensure_column(cur, "notifications", "recipient_user", "TEXT")

    seed_users = [
        ("james.walker", "CFO@Secure2025", "cfo", "James Walker"),
        ("anand.choudhary", "AP@Secure2025", "ap", "Anand Choudhary"),
        ("chirag.singh", "AP@Secure2025", "ap", "Chirag Singh"),
        ("robin.preet", "AP@Secure2025", "ap", "Robin Preet"),
    ]
    cur.executemany(
        """INSERT INTO users (username, password_hash, role, full_name)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(username) DO UPDATE SET
               password_hash = excluded.password_hash,
               role          = excluded.role,
               full_name     = excluded.full_name""",
        seed_users,
    )
    conn.commit()

    # Load reference data into the (possibly already-created empty) DB.
    _seed_reference_data(conn, cur)

    conn.commit()
    conn.close()


app = FastAPI(
    title="Payment Audit Agent"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup():
    init_db()
    print("INIT_DB COMPLETE")


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


app.include_router(upload_router)
app.include_router(decision_router)
app.include_router(websocket_router)
app.include_router(audit_router)
app.include_router(email_router)
app.include_router(auth_router)
