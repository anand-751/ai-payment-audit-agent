"""
Idempotent database initializer.

Runs on app startup so that a fresh database (for example, an empty Railway
Volume) automatically gets every table, column, index, and the seed users.
Safe to run on every boot.

First-boot behaviour:
- If the live DB at settings.DB_PATH does not exist yet, and a bundled seed DB
  ships inside the image (payment_audit.seed.db next to this file), it is copied
  to the volume so your reference data (vendor_master, invoice_register,
  payment_history) is preserved.
- Then schema/columns/users are ensured idempotently.
"""
import shutil
from pathlib import Path

from app.config import settings
from app.core.database import get_db_connection

# Optional reference-data seed shipped inside the image (rename your committed
# payment_audit.db to this filename and keep committing ONLY this seed).
SEED_DB = Path(__file__).resolve().parent / "payment_audit.seed.db"


def _ensure_column(cur, table, column, ddl_type):
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def init_db():
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # First boot on an empty volume: seed from the bundled reference DB if present
    if not db_path.exists() and SEED_DB.exists():
        shutil.copy(SEED_DB, db_path)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.executescript(
        """
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
    )

    # Make sure columns added after the original schema exist on older DBs
    _ensure_column(cur, "payment_batches", "file_path", "TEXT")
    _ensure_column(cur, "payment_batches", "cfo_comment", "TEXT")

    # Seed AP users (stored as PLAINTEXT to match the current auth_service check)
    seed_users = [
        ("chirag.singh", "AP@Secure2025", "ap", "Chirag Singh"),
        ("robin.preet",  "AP@Secure2025", "ap", "Robin Preet"),
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
    conn.close()
