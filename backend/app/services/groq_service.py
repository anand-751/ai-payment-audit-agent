"""
groq_service.py

AI narrative module ONLY.

All payment validation rules live in validation_service.py (pandas engine).
This module does NOT touch the database and does NOT re-validate anything.
It takes the already-computed `metadata` dict and produces a safe,
CFO-ready risk-mitigation narrative.

Usage from validation_service.py:
    from app.services.groq_service import generate_cfo_summary
    cfo_summary = generate_cfo_summary(metadata)
"""

import os
import re

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

print(">>> groq_service (AI narrative only) loaded <<<")

# ---------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ---------------------------------------------------
# OUTPUT WORDING CONSTANTS
# ---------------------------------------------------
_FINAL_CLOSING = (
    "Mitigation should focus on approval enforcement, duplicate-payment prevention, "
    "and amount-validation controls before CFO risk acceptance is considered."
)

# Official labels the model should use. These avoid vague wording like
# "validation issues" and broken shorthand like "duplicate- prevention".
_CATEGORY_LABELS = {
    "duplicate": "duplicate-payment exceptions",
    "approval": "approval control failures",
    "vendor": "vendor validation issues",
    "amount": "amount-validation exceptions",
    "routing": "bank-routing exceptions",
    "discount": "treasury optimization opportunities",
}

# ---------------------------------------------------
# IDENTIFIER SAFETY LAYER (input side)
# Transaction-level identifiers that must NEVER reach the LLM.
# ---------------------------------------------------
_FORBIDDEN_LLM_KEYS = (
    "duplicate_invoice_number",
    "duplicate_payment_id",
    "duplicate_info",
    "duplicate_days_ago",
    "blocked_payment_ids",
    "unapproved_payment_ids",
    "invalid_vendor_payment_id",
    "invalid_vendor_name",
    "amount_mismatch_payment_id",
    "amount_mismatch_uploaded",
    "amount_mismatch_approved",
    "amount_mismatch_difference",
    "discount_details",
    "violations",
)


def _safe_metadata_for_llm(metadata):
    """Return a copy with all transaction-level identifiers stripped out."""
    return {k: v for k, v in metadata.items() if k not in _FORBIDDEN_LLM_KEYS}


# ---------------------------------------------------
# DERIVE SCORE FIELDS  (single source of truth)
# Consumes metadata['integrity_score'] where HIGHER = SAFER,
# matching validation_service.py.
# ---------------------------------------------------
def _derive_score_fields(metadata):
    """Returns (integrity_score, financial_risk, risk_band, review_posture, band_guidance)."""
    integrity_score = float(metadata.get("integrity_score", 0.0))   # higher = safer
    financial_risk = max(0.0, 100.0 - integrity_score)              # remaining exposure

    if integrity_score >= 85:
        risk_band = "LOW RISK"
        review_posture = "STANDARD CFO REVIEW"
        band_guidance = (
            "Batch integrity is high and residual exceptions are limited; they "
            "may be reviewed and accepted at the CFO's discretion."
        )
    elif integrity_score >= 70:
        risk_band = "MEDIUM RISK"
        review_posture = "ENHANCED CFO REVIEW"
        band_guidance = (
            "Moderate control exposure is present; flagged exception groups warrant "
            "targeted review before CFO risk acceptance is considered."
        )
    else:
        risk_band = "HIGH RISK"
        review_posture = "ESCALATED MITIGATION REVIEW"
        band_guidance = (
            "Elevated control exposure is present; flagged exceptions require "
            "investigation and mitigation before CFO risk acceptance is considered."
        )

    return integrity_score, financial_risk, risk_band, review_posture, band_guidance


# ---------------------------------------------------
# BUILD CONTROLLED LLM PROMPT
# Reasons/categories only -- never identifiers.
# ---------------------------------------------------
def build_llm_prompt(metadata):
    metadata = _safe_metadata_for_llm(metadata)
    (integrity_score, financial_risk, risk_band,
     review_posture, band_guidance) = _derive_score_fields(metadata)

    return f"""You are a senior treasury risk advisor writing a CFO-ready risk-mitigation advisory from validated aggregate metrics. Your purpose is to give the CFO an overall mitigation strategy - not to summarize the dashboard, list transactions, or authorize payments.

==========================================================
ABSOLUTE RULES (NON-NEGOTIABLE)
==========================================================
- Never authorize, release, hold, approve, or reject payments. Final authorization and risk acceptance remain with the CFO or designated finance approver.
- NEVER reference any individual transaction. Never output invoice numbers, payment IDs, vendor IDs, vendor names, bank/routing details, or ANY identifier-style code (nothing like INV-, PAY-, VEN-, or letter-number codes). Refer ONLY to control CATEGORIES and their aggregate counts.
- Speak only in terms of REASON CATEGORIES using these exact labels where relevant: duplicate-payment exceptions, approval control failures, vendor validation issues, amount-validation exceptions, bank-routing exceptions, and treasury optimization opportunities.
- Never use vague labels like validation issues or duplicate exceptions. Always specify vendor validation issues, amount-validation exceptions, or duplicate-payment exceptions.
- Never shorten compound terms with dangling hyphens. Do not write duplicate- prevention, -master validation, or amount-validation and -master validation. Write duplicate-payment prevention and vendor-master validation.
- Never invent, recalculate, round, infer, or approximate figures. Never use the words: approximately, around, about, estimated, roughly. Use figures exactly as given or omit them.
- Frame the Integrity Score ONLY as the share of value cleared for disbursement; the remainder is Financial Risk exposure. Never call the Integrity Score a risk score.
- Discounts are treasury optimization opportunities only - never leakage, losses, or control failures.
- Omit any category whose count is zero. Plain text, ONE polished paragraph, 5-6 sentences. No markdown, no bullets, no identifiers.

==========================================================
VALIDATED METRICS
==========================================================
CFO Review Posture: {review_posture}
Risk Classification: {risk_band}
Integrity Classification: {metadata.get('integrity_label', risk_band)}
Integrity Score: {integrity_score:.1f}%
Financial Risk: {financial_risk:.1f}%
Total Batch Value: ${metadata['total_batch_amount']:,.0f}
High Risk Exposure: ${metadata['high_risk_exposure']:,.0f}
Blocked Payments: {metadata.get('total_blocked_payments', 0)}
Duplicate-Payment Exceptions: {metadata.get('duplicate_count', 0)}
Approval Control Failures: {metadata.get('approval_failures', 0)}
Vendor Validation Issues: {metadata.get('vendor_issues', 0)}
Amount-Validation Exceptions: {metadata.get('amount_mismatches', 0)}
Bank-Routing Exceptions: {metadata.get('routing_issues', 0)}
Treasury Optimization Opportunities: {metadata.get('discount_opportunities', 0)}
Missed Discounts: {metadata.get('discount_missed_count', 0)}

==========================================================
THIS BATCH GUIDANCE
==========================================================
{band_guidance}

==========================================================
YOUR TASK - OVERALL RISK-MITIGATION ADVISORY
==========================================================
Write ONE CFO-ready advisory paragraph that:
1. Opens with the CFO Review Posture and Risk Classification ({review_posture} - {risk_band}).
2. States the Integrity Score ({integrity_score:.1f}%) as the share of value cleared for disbursement and Financial Risk ({financial_risk:.1f}%) as remaining exposure, citing total batch value and high-risk exposure once.
3. Identifies the risk-driving control categories using only exact category labels and aggregate counts.
4. Recommends concrete process/control-level mitigation actions: approval enforcement, duplicate-payment prevention, amount-validation/reconciliation, and vendor-master validation.
5. Notes discount opportunities, if any, only as treasury optimization opportunities separate from authorization risk.
6. Reinforces that final authorization and risk acceptance remain with the CFO or designated finance approver.
7. Closes with this exact sentence: {_FINAL_CLOSING}

Be decisive about the mitigation strategy, but never make the final decision and never reference any individual transaction or identifier."""


# ---------------------------------------------------
# OUTPUT-SIDE SANITIZER
# Final guard: strip any identifier / banned wording the model might emit.
# ---------------------------------------------------
def sanitize_cfo_narrative(text):
    """Final polish + safety guard for CFO narrative output."""
    text = str(text or "")

    # Strip invoice / transaction identifiers if the model ever emits one.
    text = re.sub(
        r"\binvoice(?:\s+number)?\s*[:,]?\s*[A-Z0-9\-]+",
        "the affected duplicate-payment exception group",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:INV|PAY|VEN|REF|TXN)[-_ ]?[A-Z0-9]+\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[A-Z]{2,}[-_ ]?\d{2,}\b", "", text)

    # Remove approximation wording and unsafe discount/loss framing.
    text = re.sub(r"\b(approximately|around|about|estimated|roughly)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(financial|revenue)\s+leakage\b", "treasury optimization opportunity", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpotential losses\b", "authorization risk exposure", text, flags=re.IGNORECASE)

    # Polish common LLM wording glitches observed in the dashboard output.
    replacements = [
        (r"\bduplicate\s*-\s*prevention\b", "duplicate-payment prevention"),
        (r"\bduplicate\s+prevention\b", "duplicate-payment prevention"),
        (r"\bduplicate\s+exceptions\b", "duplicate-payment exceptions"),
        (r"\bduplicate\s+exception\b", "duplicate-payment exception"),
        (r"\bduplicate\s+payment\s+exceptions\b", "duplicate-payment exceptions"),
        (r"\bduplicate\s+payment\s+exception\b", "duplicate-payment exception"),
        (r"\band\s+-\s*master\s+validation\b", "and vendor-master validation"),
        (r"(?<![A-Za-z])-\s*master\s+validation\b", "vendor-master validation"),
        (r"\bvendorvendor-master\s+validation\b", "vendor-master validation"),
        (r"\bvendor\s+master\s+validation\b", "vendor-master validation"),
        (r"\bamount\s+validation\s+issues\b", "amount-validation exceptions"),
        (r"\bamount\s+validation\s+issue\b", "amount-validation exception"),
        (r"\bamount-validation\s+issues\b", "amount-validation exceptions"),
        (r"\bvalidation\s+issues\b", "vendor validation issues"),
        (r"\bvalidation\s+issue\b", "vendor validation issue"),
        (r"\bdiscount\s+opportunities\b", "treasury optimization opportunities"),
        (r"\bdiscount\s+opportunity\b", "treasury optimization opportunity"),
        (r"\bamount-validation\s+and\s+vendor-master\s+validation\s+controls\b", "amount-validation/reconciliation and vendor-master validation controls"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    # Ensure the required closing sentence is exact, even if the model abbreviates it.
    text = re.sub(
        r"Mitigation should focus on .*? before CFO risk acceptance is considered\.?",
        _FINAL_CLOSING,
        text,
        flags=re.IGNORECASE,
    )

    # Tidy whitespace / punctuation after removals.
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = text.replace("amount-validation and vendor-master validation controls", "amount-validation/reconciliation and vendor-master validation controls")
    text = text.strip()

    if _FINAL_CLOSING not in text:
        if text and not text.endswith("."):
            text += "."
        text = f"{text} {_FINAL_CLOSING}".strip()

    return text



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
                        "You interpret validated aggregate metrics into an executive risk-mitigation strategy - "
                        "you never summarize every metric and never authorize payments. You never mention invoice "
                        "numbers, payment IDs, vendor IDs, vendor names, bank or routing details, or any single "
                        "transaction. You never use approximately, around, about, estimated, or roughly. You never "
                        "call discounts leakage or losses. Use exact labels: duplicate-payment exceptions, "
                        "approval control failures, vendor validation issues, amount-validation exceptions, "
                        "bank-routing exceptions, treasury optimization opportunities, duplicate-payment "
                        "prevention, and vendor-master validation. Never write dangling hyphen phrases such as "
                        "duplicate- prevention or -master validation. Final authorization and risk acceptance "
                        "always remain with the CFO."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=450,
        )
        raw = response.choices[0].message.content.strip().replace('"', "")
        print("RAW LLM OUTPUT:", raw)
        return sanitize_cfo_narrative(raw)
    except Exception as exc:
        # Never let a model/network error break the report; return a safe fallback.
        integrity_score, financial_risk, risk_band, posture, _ = _derive_score_fields(metadata)
        print(f"[AI INTERPRETATION ERROR]: {exc}")
        return (
            f"{posture} - {risk_band}. Integrity Score {integrity_score:.1f}% cleared for "
            f"disbursement; Financial Risk {financial_risk:.1f}% remaining exposure. "
            + _FINAL_CLOSING
        )


# ---------------------------------------------------
# FINAL CFO SUMMARY  (public entry point)
# ---------------------------------------------------
def generate_cfo_summary(metadata):
    """Return the CFO-ready narrative paragraph for the given metadata."""
    return generate_ai_interpretation(metadata)
