import os
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

from app.core.database import get_db_connection
from app.services.decision_service import (
    generate_audit_metadata,
    update_batch_status
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
# BUILD DETERMINISTIC EXECUTIVE SUMMARY BLOCK
# (hardcoded figures — LLM cannot touch these)
# ---------------------------------------------------

def build_executive_block(metadata):

    executive_block = f"""
Batch Integrity Score: {metadata['risk_score']:.1f}%
Total Batch Value: ${metadata['total_batch_amount']:,.2f}
High Risk Exposure: ${metadata['high_risk_exposure']:,.2f}
Total Blocked Payments: {metadata['total_blocked_payments']}
Blocked Payment IDs: {', '.join(metadata.get('blocked_payment_ids', []))}
Decision Status: {metadata['decision']} ({metadata.get('integrity_label', '')})

Duplicate Payments: {metadata['duplicate_count']}
  └─ Invoice: {metadata.get('duplicate_invoice_number', 'N/A')}
  └─ Payment ID: {metadata.get('duplicate_payment_id', 'N/A')}
  └─ Amount: ${metadata.get('duplicate_amount', 0):,.2f}
  └─ Previously paid: {metadata.get('duplicate_days_ago', 'N/A')} days ago

Unapproved Payments: {metadata['approval_failures']}
  └─ Payment IDs: {', '.join(metadata.get('unapproved_payment_ids', []))}

Vendor Issues: {metadata['vendor_issues']}
  └─ Payment ID: {metadata.get('invalid_vendor_payment_id', 'N/A')}
  └─ Vendor Name: {metadata.get('invalid_vendor_name', 'N/A')}

Amount Mismatches: {metadata['amount_mismatches']}
  └─ Payment ID: {metadata.get('amount_mismatch_payment_id', 'N/A')}
  └─ Submitted: ${metadata.get('amount_mismatch_uploaded', 0):,.2f}
  └─ Approved: ${metadata.get('amount_mismatch_approved', 0):,.2f}
  └─ Difference: ${metadata.get('amount_mismatch_difference', 0):,.2f}

Routing Issues: {metadata['routing_issues']}
Discount Opportunities: {metadata['discount_opportunities']}
Discounts available: {metadata.get('discount_available_count', 0)}
Discounts missed: {metadata.get('discount_missed_count', 0)}
"""
    return executive_block.strip()


# ---------------------------------------------------
# DERIVE SCORE FIELDS  (single source of truth)
# ---------------------------------------------------

def _derive_score_fields(metadata):
    """Compute all score-derived fields from raw metadata.

    Returns a tuple:
        (integrity_score, financial_risk, risk_band, recommended_action, band_guidance)
    """
    risk_score      = float(metadata["risk_score"])          # 0–100, higher = more risky
    integrity_score = max(0.0, 100.0 - risk_score)           # higher = safer
    financial_risk  = risk_score                             # financial risk % = risk_score

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

    return integrity_score, financial_risk, risk_band, recommended_action, band_guidance


# ---------------------------------------------------
# BUILD CONTROLLED LLM PROMPT
# ---------------------------------------------------

def build_llm_prompt(metadata):

    (
        integrity_score,
        financial_risk,
        risk_band,
        recommended_action,
        band_guidance,
    ) = _derive_score_fields(metadata)

    return f"""
You are a Senior Treasury Controller preparing an executive payment risk assessment for the Chief Financial Officer (CFO).

The payment validation has already been completed by a deterministic financial control engine. Your responsibility is ONLY to convert the validated financial metrics into a strategic executive treasury risk narrative in professional financial terms to assist the CFO in making a payment authorization decision.

==========================================================
NON-NEGOTIABLE RULES
==========================================================
- NEVER invent, estimate, infer, calculate or modify any numerical value.
- NEVER change the recommended action.
- NEVER change the risk classification.
- NEVER narrate individual invoice numbers, payment IDs, vendor IDs or specific transaction details one by one.
- Speak ONLY at the payment batch level.
- Group findings by control category using aggregate counts only (e.g., "3 duplicate payment exceptions").
- Produce plain text only (one paragraph, no markdown, no bullet points, max 8 sentences).

==========================================================
VALIDATED EXECUTIVE METRICS
==========================================================
Batch Integrity Score: {integrity_score:.1f} out of 100
Financial Risk: {financial_risk:.1f}%
Risk Classification: {risk_band}
Recommended Action: {recommended_action}
Total Batch Value: ${metadata['total_batch_amount']:,.2f}
High Risk Exposure: ${metadata['high_risk_exposure']:,.2f}
Blocked Payments Count: {metadata['total_blocked_payments']}

Duplicate Payment Exceptions: {metadata['duplicate_count']}
Approval Control Failures: {metadata['approval_failures']}
Vendor Validation Issues: {metadata['vendor_issues']}
Amount Validation Issues: {metadata['amount_mismatches']}
Bank Routing Exceptions: {metadata['routing_issues']}


***REMEDIATION LANGUAGE***:
- Do not use generic remediation phrases such as "implement targeted remediation measures", "address these vulnerabilities", or "strengthen controls" without naming the control categories.
- Remediation must stay aggregate-level and category-level.
- Preferred wording: "Remediation should focus on duplicate-payment controls, approval enforcement, vendor validation, amount-matching, and routing verification."
- Only include categories that are relevant to the non-zero exception counts.

==========================================================
YOUR TASK
==========================================================
Write an executive treasury assessment narrative for the CFO in professional financial/treasury terms. One paragraph, plain text, no markdown, no bullet points, maximum 8 sentences.

FOLLOW THESE RULES EXACTLY:

INTEGRITY SCORE — CRITICAL FRAMING RULE:
- The Batch Integrity Score of {integrity_score:.1f} out of 100 means that {integrity_score:.1f}% of the total payment batch value is considered SAFE for disbursement.
- The remaining {financial_risk:.1f}% represents the financial risk exposure (blocked or flagged payments).
- NEVER describe the Integrity Score as a risk indicator, danger signal, or reason for concern by itself.
- CORRECT example: "The Batch Integrity Score of {integrity_score:.1f} out of 100 indicates that {integrity_score:.1f}% of the batch value is cleared for disbursement, with {financial_risk:.1f}% currently at financial risk exposure."
- WRONG example: "an integrity score of 69.5 out of 100, indicating a need for immediate attention..."

INDIVIDUAL TRANSACTION IDs — ABSOLUTE BAN:
- NEVER mention invoice numbers, payment IDs, vendor IDs, vendor names, bank account details, routing numbers, or any individual transaction-level identifier.
- NEVER refer to a specific invoice, payment, vendor, or transaction as an example.
- Do not use phrases such as "one notable instance", "a duplicate invoice", "the affected vendor", or any wording that implies a specific transaction.
- The narrative must scale to thousands of payments and must remain fully aggregate-level.
- ***WRONG: "one notable instance of a duplicate invoice, INV-80035"***
- WRONG: "a specific vendor failed validation"
- CORRECT: "Duplicate-payment exceptions were identified at the batch level"
- CORRECT: "Vendor validation exceptions were identified in aggregate"

CONTROL EXCEPTIONS — INCLUDE ALL NON-ZERO COUNTS:
- You MUST include every control category where the count is greater than zero.
- This includes: Duplicate Payments, Approval Failures, Vendor Issues, Amount Mismatches, AND Bank Routing Exceptions.
- If Bank Routing Exceptions is greater than 0, it MUST appear in the narrative.

DISCOUNT OBSERVATIONS — TREASURY OPTIMIZATION ONLY:
- Discount exceptions are treasury optimization items, not payment authorization risk items.
- If Discounts Available > 0, mention them as treasury optimization opportunities.
- If Discounts Missed > 0, mention them only as missed treasury optimization opportunities.
- NEVER describe missed discounts as "financial leakage", "control failure", "loss", "risk exposure", or a reason to block, hold, or flag payments.
- Use this wording when applicable: "Discount exceptions should be treated as treasury optimization items, separate from payment authorization risk."

CFO REVIEW POSTURE:
- Score >= 85: LOW RISK — Authorization Review.
- Score 70–84: MEDIUM RISK — Controlled Exception Review.
- Score < 70: HIGH RISK — Escalated Mitigation Review.
- The AI must provide the CFO review posture, not make an independent release, hold, or payment authorization decision.
- For high-risk batches, use the exact phrase: "High Risk — Escalated Mitigation Review."

NARRATIVE STRUCTURE (in this order):
1. State the CFO review posture using the Risk Classification ({risk_band}) and Recommended Action ({recommended_action}), without making an independent release/hold decision.
2. State the Integrity Score as % of batch SAFE for disbursement, and the financial risk % exposure.
3. Give the financial scale: Total Batch Value and High Risk Exposure.
4. Narrate ALL non-zero control exception categories using only aggregate counts (no individual IDs).
5. Mention discount observations (available and/or missed) as operational notes if applicable.
6. Close with a category-level remediation recommendation aligned to the CFO review posture and this guidance: "{band_guidance}"
"""

# ---------------------------------------------------
# GENERATE AI INTERPRETATION
# ---------------------------------------------------

def generate_ai_interpretation(metadata):
    prompt = build_llm_prompt(metadata)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior treasury controller and payment risk officer. "
                    "You write precise, hallucination-free, one-paragraph executive risk "
                    "assessments for a CFO in professional financial/treasury language. "
                    "You narrate overall batch-level risk strategy — never individual payments. "

                    "INTEGRITY SCORE FRAMING: The Batch Integrity Score represents the PERCENTAGE "
                    "OF BATCH VALUE SAFE FOR DISBURSEMENT. A score of 69.5 means 69.5% is safe — "
                    "it does NOT mean 'high risk' or 'needs immediate attention' by itself. "
                    "Always frame it as: X% of the batch is cleared for disbursement, Y% is at risk exposure. "

                    "ID BAN: NEVER output invoice numbers, payment IDs, vendor IDs, vendor names, "
                    "bank details, routing details, or any individual transaction-level identifier. "
                    "Never refer to a specific invoice, payment, vendor, or transaction even without naming the ID. "
                    "Use only aggregate batch-level counts and category-level control language. "

                    "ROUTING: If Bank Routing Exceptions count is greater than 0, you MUST mention it. "

                    "DISCOUNTS: Discount exceptions are treasury optimization items only, separate from "
                    "payment authorization risk. Never call missed discounts financial leakage, losses, "
                    "control failures, blockers, or risk exposure. "

                    "RISK TIERS: score >= 85 = LOW RISK safe to release; "
                    "score 70-84 = MEDIUM RISK review before release; "
                    "score < 70 = HIGH RISK hold and remediate. "

                    "You never invent, estimate or alter any figure. "
                    "You never call the Integrity Score a risk score or danger signal."

                    "Remediation language must be specific by control category: duplicate-payment controls, "
                    "approval enforcement, vendor validation, amount-matching, and routing verification. "
                    "Do not use vague phrases like 'address these vulnerabilities'. "
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=450,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------
# VALIDATE PAYMENT BATCH  ← BUGS FIXED HERE
# ---------------------------------------------------

def validate_payment_batch(batch_id):

    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT uploaded_at FROM payment_batches WHERE batch_id = ?",
        (batch_id,)
    )
    batch_row = cursor.fetchone()
    if not batch_row:
        conn.close()
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
        conn.close()
        raise ValueError(f"No payment items found for batch {batch_id}")

    violations    = []
    red_flags     = 0
    yellow_flags  = 0
    duplicate_info = None
    discount_available_count = 0
    discount_missed_count = 0
    discount_details = []

    def record_violation(payment_id, severity, violation_type, reason):
        nonlocal red_flags, yellow_flags

        # FIX 3 — single source of truth for severity counting
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

        # ── RULE 3: Vendor validation ────────────────────────────
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

            # ── RULE 5: Bank routing (YELLOW — advisory) ─────────
            if (approved_routing and bank_routing
                    and bank_routing != approved_routing):
                record_violation(
                    payment_id, "YELLOW", "BANK_ROUTING_MISMATCH",
                    f"Bank routing {bank_routing} does not match "
                    f"approved routing {approved_routing}."
                )

        # ── RULE 2: Missing approval ─────────────────────────────
        # FIX 1 — was YELLOW, must be RED
        if not authorizer or str(authorizer).strip() == "":
            record_violation(
                payment_id, "RED", "MISSING_APPROVAL",
                "Payment is missing an authorizer name."
            )

        # ── RULE 4: Amount discrepancy ───────────────────────────
        cursor.execute(
            "SELECT * FROM invoice_register WHERE invoice_number = ?",
            (invoice_number,)
        )
        invoice = cursor.fetchone()

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

        if history_row:
            record_violation(
                payment_id, "RED", "DUPLICATE_PAYMENT",
                f"Invoice {invoice_number} was already paid "
                f"on {history_row[1]}."
            )
            if not duplicate_info:
                duplicate_info = {
                    "invoice_number": invoice_number,
                    "days_ago":       _calculate_days_ago(history_row[1]),
                    "payment_id":     payment_id,
                    "amount":         float(amount),
                }

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

    # Enrich with exact duplicate details so LLM never guesses
    if duplicate_info:
        metadata["duplicate_invoice_number"] = duplicate_info["invoice_number"]
        metadata["duplicate_days_ago"]       = duplicate_info["days_ago"]
        metadata["duplicate_payment_id"]     = duplicate_info["payment_id"]
        metadata["duplicate_amount"]         = duplicate_info["amount"]

    # Enrich unapproved payment IDs
    metadata["unapproved_payment_ids"] = list({
        v["payment_id"] for v in violations
        if v["violation_type"] == "MISSING_APPROVAL"
    })

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

    # Enrich invalid vendor details
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

    executive_block    = build_executive_block(metadata)
    ai_interpretation  = generate_ai_interpretation(metadata)

    return f"{executive_block}\n\nController Assessment:\n{ai_interpretation}".strip()