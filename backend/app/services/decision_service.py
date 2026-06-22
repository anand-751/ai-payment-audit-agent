from app.core.database import get_db_connection


# ---------------------------------------------------
# GENERATE EXECUTIVE METADATA (DataFrame-based)
# Accepts pre-computed audit_result that already
# carries total_batch_amount and high_risk_exposure
# so this function never touches the database.
# ---------------------------------------------------

def generate_audit_metadata(batch_id, audit_result):
    """
    Build the metadata dict from a fully-resolved audit_result.

    audit_result keys
    -----------------
    violations          : list of violation dicts
    red_flags           : int
    yellow_flags        : int
    integrity_score          : int
    total_batch_amount  : float   ← supplied by validation_service
    high_risk_exposure  : float   ← supplied by validation_service
    blocked_payment_ids : list[str]
    """

    violations          = audit_result["violations"]
    red_flags           = audit_result["red_flags"]
    yellow_flags        = audit_result["yellow_flags"]
    integrity_score     = audit_result["integrity_score"]
    total_batch_amount  = audit_result["total_batch_amount"]
    high_risk_exposure  = audit_result["high_risk_exposure"]
    blocked_payment_ids = audit_result["blocked_payment_ids"]

    # ---------------------------------------------------
    # CATEGORY COUNTS
    # ---------------------------------------------------

    def _count(vtype):
        return sum(1 for v in violations if v["violation_type"] == vtype)

    def _count_any(vtypes):
        return sum(1 for v in violations if v["violation_type"] in vtypes)

    duplicate_count      = _count("DUPLICATE_PAYMENT")
    approval_failures    = _count("MISSING_APPROVAL")
    vendor_issues        = _count_any({"INVALID_VENDOR", "INACTIVE_VENDOR"})
    amount_mismatches    = _count("AMOUNT_MISMATCH")
    routing_issues       = _count("BANK_ROUTING_MISMATCH")
    discount_available_count = _count("EARLY_PAYMENT_DISCOUNT")

    discount_missed_count = _count("MISSED_EARLY_PAYMENT_DISCOUNT")

    discount_opportunities = (
        discount_available_count +
        discount_missed_count
    )

    total_blocked_payments = len(blocked_payment_ids)

    # ---------------------------------------------------
    # DECISION ENGINE
    # ---------------------------------------------------

    decision = "APPROVED" if (red_flags == 0 and yellow_flags == 0) else "UNDER_REVIEW"

    # ---------------------------------------------------
    # RISK LABEL
    # ---------------------------------------------------

    if integrity_score >= 85:
        integrity_label = "LOW_RISK"
    elif integrity_score >= 70:
        integrity_label = "MODERATE_RISK"
    elif integrity_score >= 50:
        integrity_label = "HIGH_RISK"
    else:
        integrity_label = "CRITICAL"

    # ---------------------------------------------------
    # FINAL METADATA
    # ---------------------------------------------------

    return {
        "batch_id":               batch_id,
        "decision":               decision,
        "integrity_score":        integrity_score,
        "integrity_label":        integrity_label,
        "total_batch_amount":     total_batch_amount,
        "high_risk_exposure":     high_risk_exposure,
        "red_flags":              red_flags,
        "yellow_flags":           yellow_flags,
        "duplicate_count":        duplicate_count,
        "approval_failures":      approval_failures,
        "vendor_issues":          vendor_issues,
        "amount_mismatches":      amount_mismatches,
        "routing_issues":         routing_issues,

        "discount_opportunities": discount_opportunities,
        "discount_available_count": discount_available_count,
        "discount_missed_count": discount_missed_count,

        "blocked_payment_ids":    blocked_payment_ids,
        "total_blocked_payments": total_blocked_payments,
    }


# ---------------------------------------------------
# UPDATE BATCH STATUS  (unchanged)
# ---------------------------------------------------

def update_batch_status(batch_id, decision):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE payment_batches SET batch_status = ? WHERE batch_id = ?",
        (decision, batch_id),
    )
    conn.commit()
    conn.close()