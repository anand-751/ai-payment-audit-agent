import io
import os
import json
​
import pandas as pd
​
from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
​
from app.core.database import get_db_connection
from app.services.csv_service import generate_batch_id
from app.services.csv_service import insert_payment_batch
​
router = APIRouter()
​
​
@router.post("/upload-payment-batch")
async def upload_payment_batch(
    files: list[UploadFile] = File(...),
    uploaded_by: str = Form(None),
    uploaded_by_name: str = Form(None),
):
    try:
        uploaded_batches = []
​
        UPLOAD_DIR = "uploads"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
​
        for file in files:
            if not file.filename.endswith(".csv"):
                continue
​
            raw_bytes = await file.read()
​
            batch_id = generate_batch_id()
​
            file_path = os.path.join(
                UPLOAD_DIR,
                f"{batch_id}_{file.filename}"
            )
​
            with open(file_path, "wb") as buffer:
                buffer.write(raw_bytes)
​
            df = pd.read_csv(io.BytesIO(raw_bytes))
​
            result = insert_payment_batch(
                df,
                file_path=file_path,
                batch_id=batch_id
            )
​
            uploaded_batches.append({
                "file_name": file.filename,
                "batch_id": batch_id,
                "batch_info": result
            })
​
        # ------------------------------------------------------------------
        # NOTIFY THE CFO: one notification row per uploaded batch.
        # The CFO frontend polls GET /notifications?role=cfo and shows these.
        # ------------------------------------------------------------------
        if uploaded_batches:
            conn = get_db_connection()
            cur = conn.cursor()
            for b in uploaded_batches:
                # Record the real filename + the AP user who uploaded this
                # batch, so the CFO list/dashboard can show them and decisions
                # can be routed back to this specific uploader.
                cur.execute(
                    """
                    UPDATE payment_batches
                    SET file_name = ?,
                        uploaded_by = ?,
                        uploaded_by_name = ?
                    WHERE batch_id = ?
                    """,
                    (
                        b["file_name"],
                        uploaded_by,
                        uploaded_by_name,
                        b["batch_id"],
                    ),
                )
​
                cur.execute(
                    """
                    INSERT INTO notifications
                        (batch_id, recipient_role, notification_type, title, message)
                    VALUES (?, 'cfo', 'NEW_BATCH', ?, ?)
                    """,
                    (
                        b["batch_id"],
                        "New batch submitted",
                        f"Batch {b['file_name']} was submitted by "
                        f"{uploaded_by_name or 'AP'} for review",
                    ),
                )
            conn.commit()
            conn.close()
​
        return {
            "success": True,
            "message": f"{len(uploaded_batches)} batches uploaded",
            "data": uploaded_batches
        }
​
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
​
​
@router.get("/batches")
async def list_batches():
    conn = get_db_connection()
    cursor = conn.cursor()
​
    cursor.execute(
        """
        SELECT
            pb.batch_id,
            pb.file_name,
            pb.uploaded_by_name,
            pb.total_items,
            pb.total_amount,
            pb.batch_status,
            pb.uploaded_at,
            COALESCE(SUM(CASE WHEN ar.severity = 'RED' THEN 1 ELSE 0 END), 0) AS red_flags,
            COALESCE(SUM(CASE WHEN ar.severity = 'YELLOW' THEN 1 ELSE 0 END), 0) AS yellow_flags
        FROM payment_batches pb
        LEFT JOIN audit_results ar
            ON pb.batch_id = ar.batch_id
        GROUP BY pb.batch_id
        ORDER BY pb.uploaded_at DESC
        """
    )
​
    rows = cursor.fetchall()
    batches = []
​
    for row in rows:
        batch_id = row["batch_id"]
        total_batch_amount = float(row["total_amount"] or 0)
​
        # Compute blocked amount from RED violations by joining payment_items
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(pi.amount), 0) AS blocked_amount,
                COUNT(*) AS blocked_count
            FROM payment_items pi
            WHERE
                pi.batch_id = ?
                AND pi.payment_id IN
                (
                    SELECT DISTINCT payment_id
                    FROM audit_results
                    WHERE
                        batch_id = ?
                        AND violation_type IN (
                            'DUPLICATE_PAYMENT',
                            'INVALID_VENDOR',
                            'INACTIVE_VENDOR',
                            'MISSING_APPROVAL',
                            'AMOUNT_MISMATCH',
                            'BANK_ROUTING_MISMATCH'
                        )
                )
            """,
            (
                batch_id,
                batch_id,
            ),
        )
​
        blocked = cursor.fetchone()
        high_risk_exposure = float(blocked["blocked_amount"] or 0)
        blocked_count = int(blocked["blocked_count"] or 0)
​
        if total_batch_amount > 0:
            integrity_score = round(
                ((total_batch_amount - high_risk_exposure) / total_batch_amount) * 100,
                1
            )
        else:
            integrity_score = 100.0
​
        batches.append({
            "id": batch_id,
            "file": row["file_name"] or batch_id,
            "uploadedBy": row["uploaded_by_name"] or "AP TEAM",
            "uploadedAt": row["uploaded_at"],
            "status": row["batch_status"],
            "payments": row["total_items"],
            "total": total_batch_amount,
​
            "integrityScore": integrity_score,
​
            "redFlags": row["red_flags"],
            "yellowFlags": row["yellow_flags"],
​
            "highRiskExposure": high_risk_exposure,
            "blockedCount": blocked_count,
        })
​
    conn.close()
​
    return {"batches": batches}
​
​
# ---------------------------------------------------
# GET FULL BATCH DETAIL  (step 7)
# Read-only: returns the stored audit pack so the CFO can open ANY batch
# (including ones uploaded by someone else) without re-running the audit.
# ---------------------------------------------------
@router.get("/batch/{batch_id}")
async def get_batch_detail(batch_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
​
    cursor.execute(
        "SELECT * FROM payment_batches WHERE batch_id = ?",
        (batch_id,),
    )
    row = cursor.fetchone()
​
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Batch not found")
​
    keys = row.keys()
​
    # Preferred path: full audit pack was persisted at audit time
    audit_json = row["audit_json"] if "audit_json" in keys else None
    if audit_json:
        conn.close()
        return json.loads(audit_json)
​
    # Fallback for batches audited before audit_json existed:
    # rebuild a minimal detail object from audit_results so the UI still renders.
    cursor.execute(
        """
        SELECT payment_id, severity, violation_type, reason
        FROM audit_results
        WHERE batch_id = ?
        """,
        (batch_id,),
    )
    violations = [
        {
            "payment_id": r["payment_id"],
            "severity": r["severity"],
            "violation_type": r["violation_type"],
            "reason": r["reason"],
        }
        for r in cursor.fetchall()
    ]
​
    total_amount = float(row["total_amount"] or 0) if "total_amount" in keys else 0.0
    status = row["batch_status"] if "batch_status" in keys else "UNDER_REVIEW"
    conn.close()
​
    return {
        "metadata": {
            "batch_id": batch_id,
            "decision": status,
            "total_batch_amount": total_amount,
        },
        "violations": violations,
        "cfo_summary": "",
    }