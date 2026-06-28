import os
import re
from datetime import datetime
​
from openai import OpenAI
from dotenv import load_dotenv
​
from app.core.database import get_db_connection
from app.services.decision_service import (
    generate_audit_metadata,
    update_batch_status
)
​
load_dotenv()
​
# ---------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------
​
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
​
​
# ---------------------------------------------------
# BUILD DETERMINISTIC EXECUTIVE SUMMARY BLOCK
# (hardcoded figures — LLM cannot touch these)
# ---------------------------------------------------
​
def build_executive_block(metadata):
​
    executive_block = f"""
Batch Integrity Score: {metadata['risk_score']:.1f}%
Total Batch Value: ${metadata['total_batch_amount']:,.2f}
High Risk Exposure: ${metadata['high_risk_exposure']:,.2f}
Total Blocked Payments: {metadata['total_blocked_payments']}
Decision Status: {metadata['decision']} ({metadata.get('integrity_label', '')})
​
Duplicate Payments: {metadata['duplicate_count']}
Unapproved Payments: {metadata['approval_failures']}
Vendor Issues: {metadata['vendor_issues']}
Vendor Validation Issues: {metadata['vendor_issues']}
Amount Mismatches: {metadata['amount_mismatches']}
Bank Routing Exceptions: {metadata['routing_issues']}
Discounts available: {metadata.get('discount_available_count', 0)}
Discounts missed: {metadata.get('discount_missed_count', 0)}
"""
    return executive_block.strip()
​
​
# ---------------------------------------------------
# DERIVE SCORE FIELDS  (single source of truth)
# ---------------------------------------------------
​
def _derive_score_fields(metadata):
    """Compute all score-derived fields from raw metadata.
​
    Returns a tuple:
        (integrity_score, financial_risk, risk_band, recommended_action, band_guidance)
    """
    risk_score      = float(metadata["risk_score"])          # 0–100, higher = more risky
    integrity_score = max(0.0, 100.0 - risk_score)           # higher = safer
    financial_risk  = risk_score                             # financial risk % = risk_score
​
    if integrity_score >= 85:
        risk_band          = "LOW RISK"
        recommended_action = metadata.get("decision", "RELEASE")
        band_guidance      = (
            "The batch integrity is high. It is safe to release the payment batch. "
            "The CFO may choose to accept any residual exceptions directly via "
            "management comments and proceed with authorization."
        )
    elif integrity_score >= 70:
        risk_band          = "MEDIUM RISK"
        recommended_action = metadata.get("decision", "PARTIAL RELEASE")
        band_guidance      = (
            "Medium risk detected. Review the flagged control exceptions before "
            "authorizing release. Consider selective blocking of high-risk line items."
        )
    else:
        risk_band          = "HIGH RISK"
        recommended_action = metadata.get("decision", "HOLD")
        band_guidance      = (
            "High risk detected. The batch must be held. Strict risk mitigations and "
            "remediation of all flagged exceptions are required before any release can "
            "be authorized."
        )
​
    return integrity_score, financial_risk, risk_band, recommended_action, band_guidance
​
​
# ---------------------------------------------------
# BUILD CONTROLLED LLM PROMPT
# ---------------------------------------------------
​
def build_llm_prompt(metadata):
​
    (
        integrity_score,
        financial_risk,
        risk_band,
        recommended_action,
        band_guidance,
    ) = _derive_score_fields(metadata)
​
    if integrity_score >= 85:
        cfo_review_posture = "Low Risk — Authorization Review"
    elif integrity_score >= 70:
        cfo_review_posture = "Medium Risk — Controlled Exception Review"
    else:
        cfo_review_posture = "High Risk — Escalated Mitigation Review"
​
    return f"""You are preparing a CFO-ready treasury risk advisory paragraph from validated aggregate payment-control metrics.

The dashboard already displays the raw numbers. Your job is not to repeat the dashboard. Your job is to interpret the metrics and advise the CFO on the overall control posture, mitigation focus, and risk-acceptance considerations.

==========================================================
NON-NEGOTIABLE RULES
==========================================================
- Do not authorize payment release.
- Do not approve, reject, release, or hold payments as a final decision.
- Do not present your output as the final payment decision.
- Final authorization and risk acceptance remain with the CFO or designated finance approver.
- Do not invent, recalculate, round, approximate, infer, or alter figures.
- Never use the words: approximately, around, about, estimated, roughly.
- Never mention invoice numbers, payment IDs, vendor IDs, vendor names, bank details, routing details, or any specific transaction.
- Never use specific-instance wording such as "a specific invoice", "one vendor", "this payment", or "a particular transaction".
- Use only batch-level counts and control categories.
- Do not list every metric mechanically.
- Do not simply restate the dashboard.
- Mention only the most decision-relevant metrics needed to support the CFO advisory judgment.
- Frame the Batch Integrity Score only as the value cleared for disbursement based on validated controls.
- Frame the remaining percentage as Financial Risk exposure.
- Never call the Batch Integrity Score a risk score.
- Discount items are operational optimization opportunities only, separate from authorization risk.
- Never describe discounts as financial leakage, revenue leakage, losses, blockers, or control failures.
- Plain text only.
- One paragraph only.
- No markdown.
- No bullet points.
- Maximum 6 sentences.

==========================================================
VALIDATED EXECUTIVE METRICS
==========================================================
CFO Review Posture: {review_posture}
Risk Classification: {risk_band}
Batch Integrity Score: {integrity_score:.1f}%
Financial Risk: {financial_risk:.1f}%
Total Batch Value: ${metadata['total_batch_amount']:,.2f}
High Risk Exposure: ${metadata['high_risk_exposure']:,.2f}
Blocked Payments: {metadata['total_blocked_payments']}

==========================================================
CONTROL EXCEPTION COUNTS
==========================================================
Approval Control Failures: {metadata['approval_failures']}
Vendor Validation Issues: {metadata['vendor_issues']}
Amount Validation Issues: {metadata['amount_mismatches']}
Bank Routing Exceptions: {metadata['routing_issues']}

==========================================================
OPERATIONAL OPTIMIZATION COUNTS
==========================================================
Discount Opportunities Available: {metadata.get('discount_available_count', 0)}
Discount Opportunities Missed: {metadata.get('discount_missed_count', 0)}

==========================================================
ADVISORY OBJECTIVE
==========================================================
Write one crisp CFO-ready treasury risk paragraph that gives professional judgment, not a metric summary.

The paragraph must:
1. Open with the CFO review posture.
2. Briefly interpret the Batch Integrity Score as the portion of value cleared for disbursement and the Financial Risk as the remaining exposure.
3. Explain what the exception pattern means for the CFO’s control review.
4. Prioritize mitigation focus by control category, using aggregate counts only where helpful.
5. Separate discount opportunities from authorization risk and frame them only as treasury optimization items.
6. Avoid transaction-level detail completely.
7. Close with this exact sentence: Mitigation should focus on approval enforcement, duplicate-payment prevention, and amount-validation controls before CFO risk acceptance is considered.

==========================================================
STYLE REQUIREMENTS
==========================================================
- Sound like a senior treasury controller advising a CFO.
- Be interpretive, not descriptive.
- Be concise and decisive, but do not make the final authorization decision.
- Do not over-repeat dashboard numbers.
- Do not mention any individual invoice, payment, vendor, or transaction.
- Every figure used must exactly match the validated metrics above."""
# ---------------------------------------------------
# GENERATE AI INTERPRETATION
# ---------------------------------------------------
​
def generate_ai_interpretation(metadata):
    prompt = build_llm_prompt(metadata)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Write one crisp CFO-ready treasury risk paragraph from validated aggregate metrics and overall professional judgement to assist cfo with treasury risk mitigation. "
                    "Do not invent, recalculate, round, approximate, or alter figures. Never use approximately, around, about, estimated, or roughly. "
                    "Never mention invoice numbers, payment IDs, vendor IDs, vendor names, bank details, routing details, or any specific transaction. "
                    "Never use specific-instance wording. Use only batch-level counts and control categories. "
                    "Open with the CFO review posture. Frame Batch Integrity Score only as value cleared for disbursement, with the remainder as financial risk exposure. "
                    "Discount items are operational optimization opportunities only, separate from authorization risk; never call them financial leakage, revenue leakage, losses, blockers, or control failures. "
                    "For high risk, use: High Risk — Escalated Mitigation Review. "
                    "Close with: Mitigation should focus on approval enforcement, duplicate-payment prevention, and amount-validation controls before CFO risk acceptance is considered."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=450,
    )
    return sanitize_cfo_narrative(response.choices[0].message.content.strip())
​
​
def sanitize_cfo_narrative(text):
    """Final safety pass to keep the CFO narrative aggregate-level and exact."""
​
    forbidden_sentence_patterns = [
        r"\bINV[-_ ]?\d+\b",
        r"\bPAY[-_ ]?\d+\b",
        r"\bpayment\s+id\b",
        r"\binvoice\s+number\b",
        r"\bspecific instance\b",
        r"\bone notable\b",
        r"\baffected vendor\b",
    ]
​
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    safe_sentences = []
    for sentence in sentences:
        if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in forbidden_sentence_patterns):
            continue
        safe_sentences.append(sentence)
​
    cleaned = " ".join(safe_sentences)
    cleaned = re.sub(r"\b(approximately|around|about|estimated|roughly)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(financial|revenue) leakage\b", "operational optimization opportunity", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpotential losses\b", "authorization risk exposure", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()
​
​
# ---------------------------------------------------
# VALIDATE PAYMENT BATCH  ← BUGS FIXED HERE
# ---------------------------------------------------
​
def validate_payment_batch(batch_id):
​
    conn   = get_db_connection()
    cursor = conn.cursor()
​
    cursor.execute(
        "SELECT uploaded_at FROM payment_batches WHERE batch_id = ?",
        (batch_id,)
    )
    batch_row = cursor.fetchone()
    if not batch_row:
        conn.close()
        raise ValueError(f"Batch not found: {batch_id}")
​
    try:
        run_date = datetime.fromisoformat(str(batch_row[0])).date()
    except ValueError:
        run_date = datetime.now().date()
​
    cursor.execute(
        "DELETE FROM audit_results WHERE batch_id = ?",
        (batch_id,)
    )
​
    cursor.execute(
        "SELECT * FROM payment_items WHERE batch_id = ?",
        (batch_id,)
    )
    items = cursor.fetchall()
​
    if not items:
        conn.close()
        raise ValueError(f"No payment items found for batch {batch_id}")
​
    violations    = []
    red_flags     = 0
    yellow_flags  = 0
    duplicate_info = None
    discount_available_count = 0
    discount_missed_count = 0
    discount_details = []
​
    def record_violation(payment_id, severity, violation_type, reason):
        nonlocal red_flags, yellow_flags
​
        # FIX 3 — single source of truth for severity counting
        if severity == "RED":
            red_flags += 1
        elif severity == "YELLOW":
            yellow_flags += 1
​
        violations.append({
            "payment_id":     payment_id,
            "severity":       severity,
            "violation_type": violation_type,
            "reason":         reason,
        })
​
        cursor.execute(
            """
            INSERT INTO audit_results
                (batch_id, payment_id, severity, violation_type, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (batch_id, payment_id, severity, violation_type, reason)
        )
​
    for item in items:
​
        payment_id     = item[0]
        vendor_id      = item[2]
        invoice_number = item[4]
        amount         = item[5]
        bank_routing   = item[6]
        authorizer     = item[7]
​
        # ── RULE 3: Vendor validation ────────────────────────────
        cursor.execute(
            "SELECT * FROM vendor_master WHERE vendor_id = ?",
            (vendor_id,)
        )
        vendor = cursor.fetchone()
​
        if not vendor:
            record_violation(
                payment_id, "RED", "INVALID_VENDOR",
                f"Vendor {vendor_id} not found in vendor master."
            )
        else:
            is_active        = vendor[5]
            approved_routing = vendor[3]
​
            if is_active in (0, "0", False, "False", "false"):
                record_violation(
                    payment_id, "RED", "INACTIVE_VENDOR",
                    f"Vendor {vendor_id} is marked inactive."
                )
​
            # ── RULE 5: Bank routing (YELLOW — advisory) ─────────
            if (approved_routing and bank_routing
                    and bank_routing != approved_routing):
                record_violation(
                    payment_id, "YELLOW", "BANK_ROUTING_MISMATCH",
                    f"Bank routing {bank_routing} does not match "
                    f"approved routing {approved_routing}."
                )
​
        # ── RULE 2: Missing approval ─────────────────────────────
        # FIX 1 — was YELLOW, must be RED
        if not authorizer or str(authorizer).strip() == "":
            record_violation(
                payment_id, "RED", "MISSING_APPROVAL",
                "Payment is missing an authorizer name."
            )
​
        # ── RULE 4: Amount discrepancy ───────────────────────────
        cursor.execute(
            "SELECT * FROM invoice_register WHERE invoice_number = ?",
            (invoice_number,)
        )
        invoice = cursor.fetchone()
​
        if invoice:
            approved_amount = invoice[2]
            if (approved_amount is not None
                    and abs(float(amount) - float(approved_amount)) > 0.01):
                # FIX 2 — was YELLOW, must be RED
                record_violation(
                    payment_id, "RED", "AMOUNT_MISMATCH",
                    f"Payment amount {amount} differs from "
                    f"approved amount {approved_amount}."
                )
        # FIX 4 — removed the bogus MISSING_APPROVAL when invoice
        # is simply not found; unknown-vendor payments won't have
        # an invoice_register entry and that is already caught by
        # the INVALID_VENDOR rule above — no double-flagging needed
​
        # ── RULE 1: Duplicate check ──────────────────────────────
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
​
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
​
        # ── RULE 6: Early payment discount (YELLOW — opportunity) 
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
            ep_discount  = ep_row[0]
            ep_deadline  = ep_row[1]
            if ep_deadline and ep_deadline not in ("N/A", ""):
                try:
                    discount_value = float(
                        str(ep_discount).replace("%", "").strip()
                    )
                except (TypeError, ValueError):
                    discount_value = 0.0
​
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
​
    conn.commit()
    conn.close()
​
    # Single consistent risk score formula
    risk_score = max(0, 100 - (red_flags * 15) - (yellow_flags * 5))
​
    audit_result = {
        "violations":   violations,
        "red_flags":    red_flags,
        "yellow_flags": yellow_flags,
        "risk_score":   risk_score,
    }
​
    # Base metadata
    metadata = generate_audit_metadata(batch_id, audit_result)
    metadata["discount_available_count"] = discount_available_count
    metadata["discount_missed_count"] = discount_missed_count
    metadata["discount_details"] = discount_details
​
    # Do not enrich CFO metadata with duplicate invoice/payment details.
    # CFO summaries must remain aggregate-level and scalable to large batches.
​
    # Enrich unapproved payment IDs
    metadata["unapproved_payment_ids"] = list({
        v["payment_id"] for v in violations
        if v["violation_type"] == "MISSING_APPROVAL"
    })
​
    # Enrich amount mismatch details
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
​
    # Enrich invalid vendor details
    inv_v = next(
        (v for v in violations if v["violation_type"] == "INVALID_VENDOR"),
        None
    )
    if inv_v:
        metadata["invalid_vendor_payment_id"] = inv_v["payment_id"]
​
    update_batch_status(batch_id, metadata["decision"])
​
    return {
        "metadata":    metadata,
        "violations":  violations,
        "cfo_summary": generate_cfo_summary(metadata),
    }
​
​
def _calculate_days_ago(payment_date_text):
    try:
        payment_date = datetime.fromisoformat(str(payment_date_text))
        return (datetime.now() - payment_date).days
    except ValueError:
        return "N/A"
​
​
# ---------------------------------------------------
# FINAL CFO SUMMARY
# ---------------------------------------------------
​
def generate_cfo_summary(metadata):
​
    executive_block    = build_executive_block(metadata)
    ai_interpretation  = generate_ai_interpretation(metadata)
​
    return f"{executive_block}\n\nController Assessment:\n{ai_interpretation}".strip()
​