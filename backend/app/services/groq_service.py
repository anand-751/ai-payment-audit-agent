import os
import re
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

from app.core.database import get_db_connection
from app.services.decision_service import (
    generate_audit_metadata,
    update_batch_status,
)

load_dotenv()

# ---------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ---------------------------------------------------
# IDENTIFIER SAFETY LAYER
# ---------------------------------------------------
# Transaction-level identifiers that must NEVER reach the LLM.
# Everything else in metadata (counts, totals, reasons-without-IDs) is
# aggregate-level and safe to pass through as-is.
_FORBIDDEN_LLM_KEYS = (
    "duplicate_invoice_number",
    "duplicate_payment_id",
    "duplicate_info",                 
    "blocked_payment_ids",
    "unapproved_payment_ids",
    "invalid_vendor_payment_id",
    "invalid_vendor_name",
    "amount_mismatch_payment_id",
    "discount_details",              
    "violations",                     
)


def _safe_metadata_for_llm(metadata):
    """Return a copy with all transaction-level identifiers stripped out.

    Only removes the specific keys above. Aggregate counts/totals/labels
    pass through untouched.
    """
    return {k: v for k, v in metadata.items() if k not in _FORBIDDEN_LLM_KEYS}


# ---------------------------------------------------
# DERIVE SCORE FIELDS  (single source of truth)
# ---------------------------------------------------
def _derive_score_fields(metadata):
    """Compute all score-derived fields from raw metadata.

    Returns a tuple:
        (integrity_score, financial_risk, risk_band, recommended_action, band_guidance)
    """
    risk_score = float(metadata["risk_score"])        # 0-100, higher = more risky
    integrity_score = max(0.0, 100.0 - risk_score)    # higher = safer
    financial_risk = risk_score                       # financial risk % = risk_score

    if integrity_score >= 85:
        risk_band = "LOW RISK"
        recommended_action = "STANDARD CFO REVIEW"
        band_guidance = (
            "Batch integrity is high and residual exceptions are limited; they "
            "may be reviewed and accepted at the CFO's discretion."
        )
    elif integrity_score >= 70:
        risk_band = "MEDIUM RISK"
        recommended_action = "ENHANCED CFO REVIEW"
        band_guidance = (
            "Moderate control exposure is present; flagged exception groups warrant "
            "targeted review before CFO risk acceptance is considered."
        )
    else:
        risk_band = "HIGH RISK"
        recommended_action = "ESCALATED MITIGATION REVIEW"
        band_guidance = (
            "Elevated control exposure is present; flagged exceptions require "
            "investigation and mitigation before CFO risk acceptance is considered."
        )

    return integrity_score, financial_risk, risk_band, recommended_action, band_guidance


# ---------------------------------------------------
# BUILD DETERMINISTIC EXECUTIVE SUMMARY BLOCK
# (hardcoded figures - LLM cannot touch these)
# ---------------------------------------------------
def build_executive_block(metadata):
    integrity_score, financial_risk, *_ = _derive_score_fields(metadata)
    executive_block = f"""Batch Integrity Score: {integrity_score:.1f}%
Financial Risk: {financial_risk:.1f}%
Total Batch Value: ${metadata['total_batch_amount']:,.2f}
High Risk Exposure: ${metadata['high_risk_exposure']:,.2f}
Total Blocked Payments: {metadata['total_blocked_payments']}
Decision Status: {metadata['decision']} ({metadata.get('integrity_label', '')})
Duplicate Payments: {metadata['duplicate_count']}
Unapproved Payments: {metadata['approval_failures']}
Vendor Validation Issues: {metadata['vendor_issues']}
Amount Mismatches: {metadata['amount_mismatches']}
Bank Routing Exceptions: {metadata['routing_issues']}
Discounts available: {metadata.get('discount_available_count', 0)}
Discounts missed: {metadata.get('discount_missed_count', 0)}"""
    return executive_block.strip()


# ---------------------------------------------------
# BUILD CONTROLLED LLM PROMPT
# ---------------------------------------------------
def build_llm_prompt(metadata):
    metadata = _safe_metadata_for_llm(metadata)
    (integrity_score, financial_risk, risk_band,
     review_posture, band_guidance) = _derive_score_fields(metadata)

    return f"""You are a senior treasury controller writing a CFO-ready risk advisory paragraph from validated aggregate metrics.

Your job is to give professional treasury judgment that helps the CFO decide - not to summarize the dashboard and not to authorize payments.

==========================================================
ABSOLUTE RULES (NON-NEGOTIABLE)
==========================================================
- Never authorize, release, hold, approve, or reject payments. Final authorization and risk acceptance remain with the CFO or designated finance approver.
- Never mention invoice numbers, payment IDs, vendor IDs, vendor names, bank or routing details, or any single transaction. No identifier-style codes of any kind.
- Never use specific-instance wording ("a specific invoice", "one notable instance", "this payment").
- Never invent, recalculate, round, infer, or approximate figures. Never use the words: approximately, around, about, estimated, roughly.
- Use figures exactly as provided, or omit them. Speak at the batch / portfolio level only.
- Frame the Batch Integrity Score ONLY as the share of value cleared for disbursement; the remainder is Financial Risk exposure. Never call the Integrity Score a risk score.
- Discount items are operational optimization opportunities only - never call them leakage, losses, blockers, or control failures.
- Group control issues by category using aggregate counts; omit any category whose count is zero.
- Plain text, one paragraph, 5-6 sentences. No markdown, no bullet points.

==========================================================
VALIDATED METRICS
==========================================================
CFO Review Posture: {review_posture}
Risk Classification: {risk_band}
Batch Integrity Score: {integrity_score:.1f}%
Financial Risk: {financial_risk:.1f}%
Total Batch Value: ${metadata['total_batch_amount']:,.2f}
High Risk Exposure: ${metadata['high_risk_exposure']:,.2f}
Blocked Payments: {metadata['total_blocked_payments']}
Duplicate Payment Exceptions: {metadata['duplicate_count']}
Approval Control Failures: {metadata['approval_failures']}
Vendor Validation Issues: {metadata['vendor_issues']}
Amount Validation Issues: {metadata['amount_mismatches']}
Bank Routing Exceptions: {metadata['routing_issues']}
Discount Opportunities Available: {metadata.get('discount_available_count', 0)}
Discount Opportunities Missed: {metadata.get('discount_missed_count', 0)}

==========================================================
THIS BATCH GUIDANCE
==========================================================
{band_guidance}

==========================================================
YOUR TASK
==========================================================
Write one crisp CFO-ready advisory paragraph that:
1. Opens with the CFO Review Posture and Risk Classification ({review_posture} - {risk_band}).
2. States the Batch Integrity Score ({integrity_score:.1f}%) as the share of value cleared for disbursement and the Financial Risk ({financial_risk:.1f}%) as the remaining exposure, then cites the total batch value and high-risk exposure once.
3. Interprets what the exception pattern means and prioritizes mitigation focus by control category (using aggregate counts only where they add value), instead of restating every metric.
4. Notes discount opportunities, if any, only as treasury optimization items separate from authorization risk.
5. Reinforces that final authorization and risk acceptance remain with the CFO or designated finance approver.
6. Closes with this exact sentence: Mitigation should focus on approval enforcement, duplicate-payment prevention, and amount-validation controls before CFO risk acceptance is considered.

Be interpretive and decisive, but never make the final decision and never reference any individual transaction."""


# ---------------------------------------------------
# GENERATE AI INTERPRETATION
# ---------------------------------------------------
def generate_ai_interpretation(metadata):
    prompt = build_llm_prompt(metadata)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior treasury controller and payment risk advisor writing for a CFO. "
                        "You interpret validated aggregate metrics into executive risk guidance - you never "
                        "summarize every metric and never authorize payments. You never mention invoice numbers, "
                        "payment IDs, vendor IDs, vendor names, bank or routing details, or any single transaction. "
                        "You never use approximately, around, about, estimated, or roughly. You never call discounts "
                        "leakage or losses. Final authorization and risk acceptance always remain with the CFO."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        print("RAW LLM OUTPUT:", response.choices[0].message.content.strip())
        return sanitize_cfo_narrative(response.choices[0].message.content.strip())
    except Exception as exc:
        # Never let a model/network error break the deterministic report.
        integrity_score, financial_risk, risk_band, action, _ = _derive_score_fields(metadata)
        return (
            f"{action} - {risk_band}. Batch Integrity Score {integrity_score:.1f}% "
            f"cleared for disbursement; Financial Risk {financial_risk:.1f}% exposure. "
            f"[AI narrative temporarily unavailable: {exc}]"
        )


def sanitize_cfo_narrative(text):
    """Final safety net on the OUTPUT side: scrub any identifier that the
    model might still produce (e.g. by inventing a plausible-looking one),
    without dropping surrounding sentences.

    This runs in addition to — not instead of — the input-side scrub in
    `_safe_metadata_for_llm`. The prompt no longer contains real invoice
    numbers, so this mainly guards against hallucinated identifiers.
    """
    # explicit "invoice <code>" or "invoice number <code>" phrasing
    text = re.sub(r"\binvoice(?:\s+number)?\s+[A-Za-z0-9\-_]+",
                  "the affected invoice group", text, flags=re.IGNORECASE)
    # identifier-style codes: INV-88219, PAY_12, VEN-7, etc.
    text = re.sub(r"\b(?:INV|PAY|VEN|REF|TXN)[-_ ]?\w+\b", "", text, flags=re.IGNORECASE)
    # generic CODE-1234 style identifiers
    text = re.sub(r"\b[A-Z]{2,}[-_ ]?\d{2,}\b", "", text)
    # banned approximation words
    text = re.sub(r"\b(approximately|around|about|estimated|roughly)\s+", "",
                  text, flags=re.IGNORECASE)
    # banned discount/loss framing
    text = re.sub(r"\b(financial|revenue)\s+leakage\b",
                  "treasury optimization opportunity", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpotential losses\b", "authorization risk exposure",
                  text, flags=re.IGNORECASE)
    # tidy whitespace/punctuation left behind by the strips above
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.])", r"\1", text)
    return text.strip()


# ---------------------------------------------------
# VALIDATE PAYMENT BATCH
# ---------------------------------------------------
def validate_payment_batch(batch_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT uploaded_at FROM payment_batches WHERE batch_id = ?",
            (batch_id,)
        )
        batch_row = cursor.fetchone()
        if not batch_row:
            raise ValueError(f"Batch not found: {batch_id}")

        try:
            run_date = datetime.fromisoformat(str(batch_row[0])).date()
        except ValueError:
            run_date = datetime.now().date()

        cursor.execute(
            "DELETE FROM audit_results WHERE batch_id = ?",
            (batch_id,)
        )

        cursor.execute(
            "SELECT * FROM payment_items WHERE batch_id = ?",
            (batch_id,)
        )
        items = cursor.fetchall()
        if not items:
            raise ValueError(f"No payment items found for batch {batch_id}")

        violations = []
        red_flags = 0
        yellow_flags = 0
        duplicate_info = None
        discount_available_count = 0
        discount_missed_count = 0
        discount_details = []

        def record_violation(payment_id, severity, violation_type, reason):
            nonlocal red_flags, yellow_flags
            # Single source of truth for severity counting
            if severity == "RED":
                red_flags += 1
            elif severity == "YELLOW":
                yellow_flags += 1

            violations.append({
                "payment_id":     payment_id,
                "severity":       severity,
                "violation_type": violation_type,
                "reason":         reason,
            })

            cursor.execute(
                """
                INSERT INTO audit_results
                    (batch_id, payment_id, severity, violation_type, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (batch_id, payment_id, severity, violation_type, reason)
            )

        for item in items:
            payment_id     = item[0]
            vendor_id      = item[2]
            invoice_number = item[4]
            amount         = item[5]
            bank_routing   = item[6]
            authorizer     = item[7]

            # -- RULE 3: Vendor validation --
            cursor.execute(
                "SELECT * FROM vendor_master WHERE vendor_id = ?",
                (vendor_id,)
            )
            vendor = cursor.fetchone()

            if not vendor:
                record_violation(
                    payment_id, "RED", "INVALID_VENDOR",
                    f"Vendor {vendor_id} not found in vendor master."
                )
            else:
                is_active        = vendor[5]
                approved_routing = vendor[3]

                if is_active in (0, "0", False, "False", "false"):
                    record_violation(
                        payment_id, "RED", "INACTIVE_VENDOR",
                        f"Vendor {vendor_id} is marked inactive."
                    )

                # -- RULE 5: Bank routing (YELLOW - advisory) --
                if (approved_routing and bank_routing
                        and bank_routing != approved_routing):
                    record_violation(
                        payment_id, "YELLOW", "BANK_ROUTING_MISMATCH",
                        f"Bank routing {bank_routing} does not match "
                        f"approved routing {approved_routing}."
                    )

            # -- RULE 2: Missing approval (RED) --
            if not authorizer or str(authorizer).strip() == "":
                record_violation(
                    payment_id, "RED", "MISSING_APPROVAL",
                    "Payment is missing an authorizer name."
                )

            # -- RULE 4: Amount discrepancy (RED) --
            cursor.execute(
                "SELECT * FROM invoice_register WHERE invoice_number = ?",
                (invoice_number,)
            )
            invoice = cursor.fetchone()

            if invoice:
                approved_amount = invoice[2]
                if (approved_amount is not None
                        and abs(float(amount) - float(approved_amount)) > 0.01):
                    record_violation(
                        payment_id, "RED", "AMOUNT_MISMATCH",
                        f"Payment amount {amount} differs from "
                        f"approved amount {approved_amount}."
                    )

            # -- RULE 1: Duplicate check (RED) --
            cursor.execute(
                """
                SELECT invoice_number, payment_date
                FROM payment_history
                WHERE invoice_number = ?
                LIMIT 1
                """,
                (invoice_number,)
            )
            history_row = cursor.fetchone()

            if history_row:
                record_violation(
                    payment_id, "RED", "DUPLICATE_PAYMENT",
                    "Duplicate payment exception identified at batch level."
                )
                if not duplicate_info:
                    duplicate_info = {
                        "invoice_number": invoice_number,
                        "days_ago":       _calculate_days_ago(history_row[1]),
                        "payment_id":     payment_id,
                        "amount":         float(amount),
                    }

            # -- RULE 6: Early payment discount (YELLOW - opportunity) --
            cursor.execute(
                """
                SELECT early_pay_discount, early_pay_deadline
                FROM payment_items
                WHERE payment_id = ? AND batch_id = ?
                """,
                (payment_id, batch_id)
            )
            ep_row = cursor.fetchone()
            if ep_row:
                ep_discount = ep_row[0]
                ep_deadline = ep_row[1]
                if ep_deadline and ep_deadline not in ("N/A", ""):
                    try:
                        discount_value = float(
                            str(ep_discount).replace("%", "").strip()
                        )
                    except (TypeError, ValueError):
                        discount_value = 0.0

                    if discount_value > 0:
                        try:
                            deadline_dt = datetime.strptime(ep_deadline, "%Y-%m-%d")
                            if run_date <= deadline_dt.date():
                                record_violation(
                                    payment_id, "YELLOW",
                                    "EARLY_PAYMENT_DISCOUNT",
                                    f"Early payment discount {discount_value}% available until {ep_deadline}."
                                )
                                discount_available_count += 1
                                discount_details.append({
                                    "payment_id": payment_id,
                                    "discount": discount_value,
                                    "deadline": ep_deadline,
                                    "status": "AVAILABLE"
                                })
                            else:
                                record_violation(
                                    payment_id, "YELLOW",
                                    "EARLY_PAYMENT_DISCOUNT",
                                    f"Early payment discount {discount_value}% "
                                    f"window missed (deadline {ep_deadline})."
                                )
                                discount_missed_count += 1
                                discount_details.append({
                                    "payment_id": payment_id,
                                    "discount": discount_value,
                                    "deadline": ep_deadline,
                                    "status": "MISSED"
                                })
                        except ValueError:
                            pass

        conn.commit()
    finally:
        conn.close()

    # Single consistent risk score formula
    risk_score = max(0, 100 - (red_flags * 15) - (yellow_flags * 5))

    audit_result = {
        "violations":   violations,
        "red_flags":    red_flags,
        "yellow_flags": yellow_flags,
        "risk_score":   risk_score,
    }

    # Base metadata
    metadata = generate_audit_metadata(batch_id, audit_result)
    metadata["discount_available_count"] = discount_available_count
    metadata["discount_missed_count"] = discount_missed_count
    metadata["discount_details"] = discount_details

    # Do not enrich CFO metadata with duplicate invoice/payment details.
    # CFO summaries must remain aggregate-level and scalable to large batches.
    # (duplicate_info itself is intentionally never written into `metadata` —
    # it exists only for potential internal/UI use, never for the LLM path.)

    # Enrich unapproved payment IDs (internal use only; stripped before LLM
    # by both the key-name filter AND the nested-structure drop in
    # `_safe_metadata_for_llm`)
    metadata["unapproved_payment_ids"] = list({
        v["payment_id"] for v in violations
        if v["violation_type"] == "MISSING_APPROVAL"
    })

    # Enrich amount mismatch details (internal use only; stripped before LLM)
    amt_v = next(
        (v for v in violations if v["violation_type"] == "AMOUNT_MISMATCH"),
        None
    )
    if amt_v:
        # Parse amounts from reason string as fallback
        reason = amt_v["reason"]
        try:
            parts = reason.replace("Payment amount ", "").split(" differs from approved amount ")
            metadata["amount_mismatch_payment_id"] = amt_v["payment_id"]
            metadata["amount_mismatch_uploaded"]   = float(parts[0])
            metadata["amount_mismatch_approved"]   = float(parts[1].rstrip("."))
            metadata["amount_mismatch_difference"] = round(
                float(parts[0]) - float(parts[1].rstrip(".")), 2
            )
        except Exception:
            pass

    # Enrich invalid vendor details (internal use only; stripped before LLM)
    inv_v = next(
        (v for v in violations if v["violation_type"] == "INVALID_VENDOR"),
        None
    )
    if inv_v:
        metadata["invalid_vendor_payment_id"] = inv_v["payment_id"]

    update_batch_status(batch_id, metadata["decision"])

    return {
        "metadata":    metadata,
        "violations":  violations,
        "cfo_summary": generate_cfo_summary(metadata),
    }


def _calculate_days_ago(payment_date_text):
    try:
        payment_date = datetime.fromisoformat(str(payment_date_text))
        return (datetime.now() - payment_date).days
    except ValueError:
        return "N/A"


# ---------------------------------------------------
# FINAL CFO SUMMARY
# ---------------------------------------------------
def generate_cfo_summary(metadata):
    executive_block = build_executive_block(metadata)
    ai_interpretation = generate_ai_interpretation(metadata)
    return f"{executive_block}\n\nController Assessment:\n{ai_interpretation}".strip()