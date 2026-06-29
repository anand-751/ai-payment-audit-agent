import os
from datetime import datetime
import gc
import pandas as pd
from dotenv import load_dotenv
from app.services.groq_service import generate_cfo_summary
from app.core.database import get_db_connection
from app.services.decision_service import (
    generate_audit_metadata,
    update_batch_status,
    save_audit_result,
)

load_dotenv()

# ---------------------------------------------------
# VIOLATION TYPES THAT BLOCK A PAYMENT
# ---------------------------------------------------

BLOCKING_VIOLATIONS = {
    "DUPLICATE_PAYMENT",
    "INVALID_VENDOR",
    "INACTIVE_VENDOR",
    "MISSING_APPROVAL",
    "AMOUNT_MISMATCH",
    "BANK_ROUTING_MISMATCH",
}

# ---------------------------------------------------
# DATABASE LOADER  — single connection, three tables
# ---------------------------------------------------

def _load_reference_dataframes(batch_id: str):
    """
    Opens ONE connection, pulls payment_items for this batch plus the
    three reference tables in full, then closes.  Returns four DataFrames.
    """
    conn = get_db_connection()

    df_batch = pd.read_sql_query(
        "SELECT * FROM payment_items WHERE batch_id = ?",
        conn,
        params=(batch_id,),
    )

    df_vendors = pd.read_sql_query(
        "SELECT vendor_id, approved_bank_routing, is_active FROM vendor_master",
        conn,
    )

    df_invoices = pd.read_sql_query(
        "SELECT invoice_number, approved_invoice_amount FROM invoice_register",
        conn,
    )

    df_history = pd.read_sql_query(
        "SELECT invoice_number, payment_date FROM payment_history",
        conn,
    )

    conn.close()

    # ---- normalise column names to lowercase snake_case ----
    for df in (df_batch, df_vendors, df_invoices, df_history):
        df.columns = [
            c.strip().lower().replace(" ", "_")
            for c in df.columns
        ]

    return df_batch, df_vendors, df_invoices, df_history


# ---------------------------------------------------
# RULE ENGINE — pure-pandas, zero per-row DB calls
# ---------------------------------------------------

def _run_rules(df_batch, df_vendors, df_invoices, df_history):
    """
    Applies all six validation rules via vectorised operations.
    Returns a list of violation dicts (same schema as before).
    """
    violations = []

    # ── join batch with vendor master (left join to catch missing vendors) ──
    merged = df_batch.merge(
        df_vendors,
        on="vendor_id",
        how="left",
        suffixes=("", "_vm"),
    )

    # ── join with invoice register ──
    merged = merged.merge(
        df_invoices,
        on="invoice_number",
        how="left",
        suffixes=("", "_ir"),
    )

    # ── join with payment history ──
    merged = merged.merge(
        df_history,
        on="invoice_number",
        how="left",
        suffixes=("", "_hist"),
    )

    # -----------------------------------------------------------------
    # RULE 1 — INVALID VENDOR (vendor not in vendor master)
    # -----------------------------------------------------------------
    mask_invalid = merged["is_active"].isna()          # NaN means no join hit
    for _, row in merged[mask_invalid].iterrows():
        violations.append(_viol(row, "RED", "INVALID_VENDOR",
            f"Vendor {row['vendor_id']} not found in vendor master."))

    # rows with a valid vendor row
    valid_vendor = merged[~mask_invalid].copy()

    # -----------------------------------------------------------------
    # RULE 2 — INACTIVE VENDOR
    # -----------------------------------------------------------------
    def _is_inactive(val):
        return str(val).strip().lower() in ("0", "false")

    mask_inactive = valid_vendor["is_active"].apply(_is_inactive)
    for _, row in valid_vendor[mask_inactive].iterrows():
        violations.append(_viol(row, "RED", "INACTIVE_VENDOR",
            f"Vendor {row['vendor_id']} is marked inactive."))

    # -----------------------------------------------------------------
    # RULE 3 — BANK ROUTING MISMATCH
    # -----------------------------------------------------------------
    mask_routing = (
        valid_vendor["approved_bank_routing"].notna()
        & valid_vendor["bank_routing"].notna()
        & (
            valid_vendor["bank_routing"]
            != valid_vendor["approved_bank_routing"]
        )
    )

    for _, row in valid_vendor[mask_routing].iterrows():
        violations.append(_viol(row, "RED", "BANK_ROUTING_MISMATCH",
            f"Bank routing {row['bank_routing']} does not match "
            f"approved routing {row['approved_bank_routing']}."))

    # -----------------------------------------------------------------
    # RULE 4 — MISSING APPROVAL
    # -----------------------------------------------------------------
    mask_no_auth = merged["authorizer"].isna() | (merged["authorizer"].astype(str).str.strip() == "")
    for _, row in merged[mask_no_auth].iterrows():
        violations.append(_viol(row, "YELLOW", "MISSING_APPROVAL",
            "Payment is missing an approver."))

    # -----------------------------------------------------------------
    # RULE 5 — AMOUNT MISMATCH / UNREGISTERED INVOICE
    # -----------------------------------------------------------------
    # Unregistered — no invoice register hit
    mask_unregistered = merged["approved_invoice_amount"].isna()
    for _, row in merged[mask_unregistered].iterrows():
        violations.append(_viol(row, "Red", "UNREGISTERED_INVOICE",
            f"Invoice {row['invoice_number']} is not registered for approval."))

    # Amount mismatch — registered but amounts differ
    registered = merged[~mask_unregistered].copy()
    registered["approved_invoice_amount"] = registered["approved_invoice_amount"].astype(float)
    registered["amount"] = registered["amount"].astype(float)
    mask_mismatch = (registered["amount"] - registered["approved_invoice_amount"]).abs() > 0.01
    for _, row in registered[mask_mismatch].iterrows():
        violations.append(_viol(row, "YELLOW", "AMOUNT_MISMATCH",
            f"Payment amount {row['amount']} differs from "
            f"approved amount {row['approved_invoice_amount']}."))

    # -----------------------------------------------------------------
    # RULE 6 — DUPLICATE PAYMENT
    # -----------------------------------------------------------------
    mask_dup = merged["payment_date"].notna()          
    for _, row in merged[mask_dup].iterrows():
        violations.append(_viol(row, "RED", "DUPLICATE_PAYMENT",
            f"Invoice {row['invoice_number']} was already paid "
            f"on {row['payment_date']}."))


    # -----------------------------------------------------------------
    # RULE 7 — EARLY PAYMENT DISCOUNT
    # -----------------------------------------------------------------

    today = pd.Timestamp.now().normalize()

    if (
        "early_pay_discount" in merged.columns
        and "early_pay_deadline" in merged.columns
    ):

        discount_df = merged.copy()

        discount_df["early_pay_discount"] = (
            discount_df["early_pay_discount"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.strip()
        )

        discount_df["early_pay_discount"] = pd.to_numeric(
            discount_df["early_pay_discount"],
            errors="coerce"
        ).fillna(0)

        discount_df["early_pay_deadline"] = pd.to_datetime(
            discount_df["early_pay_deadline"],
            errors="coerce"
        )

        print("\nDISCOUNT DEBUG")
        print(discount_df[
            [
                "payment_id",
                "early_pay_discount",
                "early_pay_deadline"
            ]
        ].head(10))

        # valid discounts only
        valid_discount_mask = (
            discount_df["early_pay_discount"] > 0
        ) & (
            discount_df["early_pay_deadline"].notna()
        )

        valid_discount_df = discount_df[valid_discount_mask]

        # AVAILABLE
        available_mask = (
            valid_discount_df["early_pay_deadline"] >= today
        )

        for _, row in valid_discount_df[available_mask].iterrows():
            violations.append(_viol(
                row,
                "YELLOW",
                "EARLY_PAYMENT_DISCOUNT",
                f"{row['early_pay_discount']}% early payment discount available until "
                f"{row['early_pay_deadline'].date()}."
            ))

        # MISSED
        missed_mask = (
            valid_discount_df["early_pay_deadline"] < today
        )

        for _, row in valid_discount_df[missed_mask].iterrows():
            violations.append(_viol(
                row,
                "YELLOW",
                "MISSED_EARLY_PAYMENT_DISCOUNT",
                f"Missed {row['early_pay_discount']}% discount opportunity. "
                f"Deadline was {row['early_pay_deadline'].date()}."
            ))

    return violations, merged


def _viol(row, severity, vtype, reason):
    return {
        "payment_id":     row["payment_id"],
        "vendor":         row.get("vendor_name", None) if hasattr(row, "get") else None,
        "amount":         float(row["amount"]) if "amount" in row.index and row["amount"] is not None else None,
        "severity":       severity,
        "violation_type": vtype,
        "reason":         reason,
    }


# ---------------------------------------------------
# PERSIST AUDIT RESULTS IN BULK
# ---------------------------------------------------

def _persist_audit_results(batch_id, violations):
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM audit_results WHERE batch_id = ?",
        (batch_id,),
    )

    if violations:
        cursor.executemany(
            """
            INSERT INTO audit_results
                (batch_id, payment_id, severity, violation_type, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (batch_id, v["payment_id"], v["severity"],
                 v["violation_type"], v["reason"])
                for v in violations
            ],
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------
# SCORE + BLOCKED PAYMENTS (vectorised)
# ---------------------------------------------------

def _score(violations, df_batch):

    red_flags = sum(
        1 for v in violations
        if v["severity"] == "RED"
    )

    NON_RISK_YELLOW_TYPES = {
        "EARLY_PAYMENT_DISCOUNT",
        "MISSED_EARLY_PAYMENT_DISCOUNT",
    }

    yellow_flags = sum(
        1 for v in violations
        if (
            v["severity"] == "YELLOW"
            and v["violation_type"] not in NON_RISK_YELLOW_TYPES
        )
    )

    # -----------------------------------------
    # Identify blocked payments
    # -----------------------------------------
    blocked_ids = list({
        v["payment_id"]
        for v in violations
        if v["violation_type"] in BLOCKING_VIOLATIONS
    })

    # -----------------------------------------
    # Financial exposure
    # -----------------------------------------
    total_batch_amount = float(df_batch["amount"].sum())

    blocked_amounts = df_batch.loc[
        df_batch["payment_id"].isin(blocked_ids),
        "amount",
    ].sum()

    high_risk_exposure = float(blocked_amounts)

    # -----------------------------------------
    # Integrity Score (Value-Based)
    # -----------------------------------------
    if total_batch_amount > 0:
        integrity_score = round(
            (
                (total_batch_amount - high_risk_exposure)
                / total_batch_amount
            ) * 100,
            1,
        )
    else:
        integrity_score = 100.0

    return (
        red_flags,
        yellow_flags,
        integrity_score,
        blocked_ids,
        total_batch_amount,
        high_risk_exposure,
    )

# ---------------------------------------------------
# DUPLICATE INFO HELPER
# ---------------------------------------------------

def _first_duplicate_info(violations, merged):
    for v in violations:
        if v["violation_type"] == "DUPLICATE_PAYMENT":
            row = merged.loc[merged["payment_id"] == v["payment_id"]].iloc[0]
            days_ago = _calculate_days_ago(str(row["payment_date"]))
            return {
                "invoice_number": row["invoice_number"],
                "days_ago":       days_ago,
            }
    return None


def _calculate_days_ago(payment_date_text):
    try:
        payment_date = datetime.fromisoformat(payment_date_text)
        return (datetime.now() - payment_date).days
    except (ValueError, TypeError):
        return "N/A"


# ---------------------------------------------------
# BUILD EXECUTIVE BLOCK  (deterministic section)
# ---------------------------------------------------

# def build_executive_block(metadata):
#     block = f"""
# Batch Integrity Score: {metadata['risk_score']}/100

# Total Batch Value: ${metadata['total_batch_amount']:,.0f}

# High Risk Exposure: ${metadata['high_risk_exposure']:,.0f}

# Blocked Payments: {metadata['total_blocked_payments']}

# Decision Status: {metadata['decision']}

# Duplicate Payments Detected: {metadata['duplicate_count']}

# Unapproved Payments: {metadata['approval_failures']}

# Vendor Issues: {metadata['vendor_issues']}

# Amount Mismatches: {metadata['amount_mismatches']}
# """.strip()

#     discount_lines = []
#     for key, label in [
#         ("discount_opportunities", "Discount Opportunities"),
#         ("discount_available_count", "Discounts Available"),
#         ("discount_missed_count", "Discounts Missed"),
#     ]:
#         if metadata.get(key) is not None:
#             discount_lines.append(f"{label}: {metadata[key]}")

#     if discount_lines:
#         block += "\n\nDiscounts:\n" + "\n".join(discount_lines)

#     return block


# (AI narrative is delegated to groq_service.generate_cfo_summary)


# ---------------------------------------------------
# MAIN ENTRY POINT — validate_payment_batch
# ---------------------------------------------------

def validate_payment_batch(batch_id: str):
        # ── 1. single DB round-trip: load all four DataFrames ──
        df_batch, df_vendors, df_invoices, df_history = _load_reference_dataframes(batch_id)

        if df_batch.empty:
            raise ValueError(f"No payment items found for batch {batch_id}")

        # ── 2. run all six rules via vectorised pandas ──
        violations, merged = _run_rules(df_batch, df_vendors, df_invoices, df_history)

        discount_available_count = sum(
            1 for v in violations
            if v["violation_type"] == "EARLY_PAYMENT_DISCOUNT"
        )

        discount_missed_count = sum(
            1 for v in violations
            if v["violation_type"] == "MISSED_EARLY_PAYMENT_DISCOUNT"
        )

        discount_opportunities = (
            discount_available_count +
            discount_missed_count
        )

        # ── 3. persist violations in one bulk INSERT ──
        _persist_audit_results(batch_id, violations)

        # ── 4. score ──
        (
            red_flags,
            yellow_flags,
            integrity_score,
            blocked_ids,
            total_batch_amount,
            high_risk_exposure,
        ) = _score(violations, df_batch)

        # ── 5. build audit_result (all pre-computed — no DB needed in metadata fn) ──
        audit_result = {
            "violations": violations,
            "red_flags": red_flags,
            "yellow_flags": yellow_flags,
            "integrity_score": integrity_score,
            "total_batch_amount": total_batch_amount,
            "high_risk_exposure": high_risk_exposure,
            "blocked_payment_ids": blocked_ids,

            # NEW
            "discount_opportunities": discount_opportunities,
            "discount_available_count": discount_available_count,
            "discount_missed_count": discount_missed_count,
        }

        metadata = generate_audit_metadata(batch_id, audit_result)

        # ── 6. enrich with first duplicate detail ──
        dup_info = _first_duplicate_info(violations, merged)
        if dup_info:
            metadata["duplicate_days_ago"] = dup_info["days_ago"]

        # ── 7. persist batch decision ──
        update_batch_status(batch_id, metadata["decision"])

        cfo_summary = generate_cfo_summary(metadata)

        response = {
            "metadata": metadata,
            "violations": violations,
            "cfo_summary": cfo_summary,
        }

        save_audit_result(batch_id, response)
        
        # ----------------------------------
        # Memory Cleanup
        # ----------------------------------

        del df_batch
        del df_vendors
        del df_invoices
        del df_history
        del merged
        del audit_result

        gc.collect()

        return response