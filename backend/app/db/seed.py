import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / "app" / "db" / "payment_audit.db"
SCHEMA_PATH = BASE_DIR / "app" / "db" / "schema.sql"
DATA_DIR = BASE_DIR / "data" / "synthetic"

if DATABASE_PATH.exists():
    DATABASE_PATH.unlink()

conn = sqlite3.connect(DATABASE_PATH)

# ---------------------------------------------------
# CREATE TABLES
# ---------------------------------------------------

with open(SCHEMA_PATH, "r") as f:
    schema_sql = f.read()

conn.executescript(schema_sql)

print("✅ Database schema created.")

# ---------------------------------------------------
# LOAD CSV FILES
# ---------------------------------------------------

vendor_df = pd.read_csv(DATA_DIR / "vendor_master.csv")

history_df = pd.read_csv(DATA_DIR / "payment_history.csv")

invoice_df = pd.read_csv(DATA_DIR / "invoice_register.csv")

# ---------------------------------------------------
# INSERT DATA
# ---------------------------------------------------

vendor_df.to_sql(
    "vendor_master",
    conn,
    if_exists="append",
    index=False
)


history_df.to_sql(
    "payment_history",
    conn,
    if_exists="append",
    index=False
)


invoice_df.to_sql(
    "invoice_register",
    conn,
    if_exists="append",
    index=False
)


conn.commit()
conn.close()

print("Sample data inserted into the database.")