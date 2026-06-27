# import sqlite3
# import uuid
# import pandas as pd
# from datetime import datetime
# from fastapi import HTTPException

# from app.core.database import get_db_connection


# REQUIRED_COLUMNS = [
#     "payment_id",
#     "vendor_id",
#     "vendor_name",
#     "invoice_number",
#     "amount",
#     "bank_routing",
#     "authorizer",
#     "due_date",
#     "invoice_date",
#     "early_pay_discount",
#     "early_pay_deadline"
# ]


# def validate_csv_schema(df: pd.DataFrame):

#     missing_columns = [
#         col for col in REQUIRED_COLUMNS
#         if col not in df.columns
#     ]

#     if missing_columns:
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "message": "Invalid payment batch schema",
#                 "missing_columns": missing_columns
#             }
#         )


# def validate_payment_ids(df: pd.DataFrame):
#     duplicate_ids = df[df.duplicated("payment_id", keep=False)]["payment_id"].unique().tolist()
#     if duplicate_ids:
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "message": "Duplicate payment IDs found in uploaded batch.",
#                 "duplicate_ids": duplicate_ids
#             }
#         )


# def generate_batch_id():

#     timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

#     random_suffix = str(uuid.uuid4())[:6]

#     return f"BATCH-{timestamp}-{random_suffix}"


# def insert_payment_batch(df: pd.DataFrame, file_path: str = None, batch_id: str = None):

#     validate_csv_schema(df)
#     validate_payment_ids(df)

#     if batch_id is None:
#         batch_id = generate_batch_id()

#     conn = get_db_connection()

#     cursor = conn.cursor()

#     # ---------------------------------------------------
#     # CALCULATE BATCH METRICS
#     # ---------------------------------------------------

#     total_items = len(df)

#     total_amount = float(df["amount"].sum())

#     # ---------------------------------------------------
#     # INSERT INTO payment_batches
#     # ---------------------------------------------------

#     cursor.execute("PRAGMA table_info(payment_batches)")
#     columns = {row[1] for row in cursor.fetchall()}

#     if "file_path" not in columns:
#         cursor.execute("ALTER TABLE payment_batches ADD COLUMN file_path TEXT")

#     cursor.execute(
#         """
#         INSERT INTO payment_batches (
#             batch_id,
#             total_items,
#             total_amount,
#             batch_status,
#             file_path
#         )
#         VALUES (?, ?, ?, ?, ?)
#         """,
#         (
#             batch_id,
#             total_items,
#             total_amount,
#             "PENDING_REVIEW",
#             file_path
#         )
#     )

#     # ---------------------------------------------------
#     # INSERT INTO payment_items
#     # ---------------------------------------------------

#     df["batch_id"] = batch_id

#     insert_df = df[[
#         "payment_id",
#         "batch_id",
#         "vendor_id",
#         "vendor_name",
#         "invoice_number",
#         "amount",
#         "bank_routing",
#         "authorizer",
#         "due_date",
#         "invoice_date",
#         "early_pay_discount",
#         "early_pay_deadline"
#     ]]

#     try:
#         insert_df.to_sql(
#             "payment_items",
#             conn,
#             if_exists="append",
#             index=False
#         )
#         conn.commit()
#     except sqlite3.IntegrityError as exc:
#         conn.rollback()
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "message": "Duplicate payment ID or constraint violation during batch insert.",
#                 "error": str(exc)
#             }
#         )

#     conn.close()

#     return {
#         "batch_id": batch_id,
#         "total_items": total_items,
#         "total_amount": total_amount,
#         "status": "PENDING_REVIEW"
#     }


import sqlite3
import uuid
import pandas as pd
from datetime import datetime
from fastapi import HTTPException

from app.core.database import get_db_connection


REQUIRED_COLUMNS = [
    "payment_id",
    "vendor_id",
    "vendor_name",
    "invoice_number",
    "amount",
    "bank_routing",
    "authorizer",
    "due_date",
    "invoice_date",
    "early_pay_discount",
    "early_pay_deadline"
]


def validate_csv_schema(df: pd.DataFrame):

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid payment batch schema",
                "missing_columns": missing_columns
            }
        )


def validate_payment_ids(df: pd.DataFrame):
    duplicate_ids = df[df.duplicated("payment_id", keep=False)]["payment_id"].unique().tolist()
    if duplicate_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Duplicate payment IDs found in uploaded batch.",
                "duplicate_ids": duplicate_ids
            }
        )


def generate_batch_id():

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    random_suffix = str(uuid.uuid4())[:6]

    return f"BATCH-{timestamp}-{random_suffix}"


def insert_payment_batch(df: pd.DataFrame, file_path: str = None, batch_id: str = None):

    validate_csv_schema(df)
    validate_payment_ids(df)

    if batch_id is None:
        batch_id = generate_batch_id()

    conn = get_db_connection()

    cursor = conn.cursor()

    # ---------------------------------------------------
    # CALCULATE BATCH METRICS
    # ---------------------------------------------------

    total_items = len(df)

    total_amount = float(df["amount"].sum())

    # ---------------------------------------------------
    # INSERT INTO payment_batches
    # ---------------------------------------------------

    cursor.execute("PRAGMA table_info(payment_batches)")
    columns = {row[1] for row in cursor.fetchall()}

    if "file_path" not in columns:
        cursor.execute("ALTER TABLE payment_batches ADD COLUMN file_path TEXT")

    cursor.execute(
        """
        INSERT INTO payment_batches (
            batch_id,
            total_items,
            total_amount,
            batch_status,
            file_path
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            batch_id,
            total_items,
            total_amount,
            "UNDER_REVIEW",
            file_path
        )
    )

    # ---------------------------------------------------
    # INSERT INTO payment_items
    # ---------------------------------------------------

    df["batch_id"] = batch_id

    insert_df = df[[
        "payment_id",
        "batch_id",
        "vendor_id",
        "vendor_name",
        "invoice_number",
        "amount",
        "bank_routing",
        "authorizer",
        "due_date",
        "invoice_date",
        "early_pay_discount",
        "early_pay_deadline"
    ]]

    try:
        insert_df.to_sql(
            "payment_items",
            conn,
            if_exists="append",
            index=False
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Duplicate payment ID or constraint violation during batch insert.",
                "error": str(exc)
            }
        )

    conn.close()

    return {
        "batch_id": batch_id,
        "total_items": total_items,
        "total_amount": total_amount,
        "status": "UNDER_REVIEW"
    }