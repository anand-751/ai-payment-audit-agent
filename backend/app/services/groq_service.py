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
# BUILD CONTROLLED LLM PROMPT
# ---------------------------------------------------

def build_llm_prompt(metadata):

    integrity_score = 100 - metadata["risk_score"]

    return f"""
You are a Senior Treasury Controller preparing an executive payment authorization summary for the Chief Financial Officer (CFO).

The audit results below are produced by a deterministic payment validation engine. Every number has already been verified.

CRITICAL INSTRUCTIONS

- NEVER invent, estimate, infer or modify any figures.
- Use ONLY the values provided below.
- NEVER refer to the Batch Integrity Score as a Risk Score.
- A higher Batch Integrity Score means MORE of the batch value is safe for payment.
- Financial Risk is the remaining percentage of the batch value currently exposed to blocked payments.
- NEVER state that a higher Integrity Score indicates higher risk.
- Keep the summary executive, concise and natural.
- No markdown.
- No bullet points.
- One paragraph only.
- 6–8 sentences maximum.

VALIDATED METRICS

Batch Integrity Score: {integrity_score:.1f}%

Financial Risk: {financial_risk:.1f}%

Total Batch Value:
${metadata['total_batch_amount']:,.2f}

High Risk Exposure:
${metadata['high_risk_exposure']:,.2f}

Decision:
{metadata['decision']}

Integrity Classification:
{metadata['integrity_label']}

Blocked Payments:
{metadata['total_blocked_payments']}

Duplicate Payments:
{metadata['duplicate_count']}

Duplicate Invoice:
{metadata.get('duplicate_invoice_number', 'N/A')}

Duplicate Payment ID:
{metadata.get('duplicate_payment_id', 'N/A')}

Duplicate Amount:
${metadata.get('duplicate_amount', 0):,.2f}

Previously Paid:
{metadata.get('duplicate_days_ago', 'N/A')} days ago

Approval Failures:
{metadata['approval_failures']}

Unapproved Payment IDs:
{', '.join(metadata.get('unapproved_payment_ids', []))}

Vendor Issues:
{metadata['vendor_issues']}

Routing Issues:
{metadata['routing_issues']}

Amount Mismatches:
{metadata['amount_mismatches']}

Amount Mismatch Payment:
{metadata.get('amount_mismatch_payment_id', 'N/A')}

Submitted Amount:
${metadata.get('amount_mismatch_uploaded', 0):,.2f}

Approved Amount:
${metadata.get('amount_mismatch_approved', 0):,.2f}

Discount Opportunities:
{metadata['discount_opportunities']}

Discounts Available:
{metadata.get('discount_available_count', 0)}

Discounts Missed:
{metadata.get('discount_missed_count', 0)}

YOUR TASK

Write an executive treasury assessment suitable for a CFO making a payment authorization decision.

The summary must:

1. Begin with the payment recommendation (RELEASE, HOLD or PARTIAL RELEASE).

2. State the Batch Integrity Score ({integrity_score:.1f}%) and explain that it represents the percentage of the total payment value considered safe for disbursement.

3. State the Financial Risk ({financial_risk:.1f}%) and explain that it represents the percentage of the batch value currently exposed to blocked payments.

4. Mention the total batch value and the high-risk exposure amount.

5. Summarize the key control failures including duplicate payments, vendor issues, routing issues, approval failures and amount mismatches only if they exist.

6. Mention available or missed discount opportunities only as operational observations, never as reasons to block payment.

7. Finish with a single, definitive treasury recommendation explaining whether the batch should be released, partially released or held.

Remember:

- Never call the Batch Integrity Score a Risk Score.
- Never say "low risk with an integrity score of XX%".
- The Integrity Score measures SAFE payment value.
- Financial Risk measures AT-RISK payment value.
- Every numerical value must exactly match the validated metrics above.
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
                    "You are a senior treasury controller "
                    "and payment risk officer. You write "
                    "precise, unambiguous executive summaries. "
                    "You never invent figures."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=180
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

    # FIX 3 — single consistent risk score formula
    # risk_score = max(0, 100 - (red_flags * 15) - (yellow_flags * 5))

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