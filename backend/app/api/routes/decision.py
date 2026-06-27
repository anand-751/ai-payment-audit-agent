from app.services.websocket_manager import manager
from fastapi import APIRouter
from pydantic import BaseModel
​
from app.core.database import get_db_connection
​
router = APIRouter()
​
​
class DecisionRequest(BaseModel):
    batch_id: str
    file_name: str
    decision: str
    comment: str = ""
​
​
@router.post("/batch-decision")
async def save_decision(req: DecisionRequest):
​
    conn = get_db_connection()
    cur = conn.cursor()
​
    # update batch status
    cur.execute(
        """
        UPDATE payment_batches
        SET batch_status = ?
        WHERE batch_id = ?
        """,
        (
            req.decision,
            req.batch_id
        )
    )
​
    # insert decision history
    cur.execute(
        """
        INSERT INTO batch_decision_history
        (
            batch_id,
            file_name,
            decision,
            decided_by,
            comment
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            req.batch_id,
            req.file_name,
            req.decision,
            "JAMES WALKER",
            req.comment
        )
    )
​
    # ------------------------------------------------------------------
    # NOTIFY THE AP TEAM about the CFO decision (APPROVED or REJECTED).
    # The AP frontend polls GET /notifications?role=ap and shows these.
    # ------------------------------------------------------------------
    nice = "approved" if req.decision == "APPROVED" else "rejected"
​
    # Find the AP user who uploaded this batch so the decision notification
    # goes ONLY to them (not every AP user).
    cur.execute(
        "SELECT uploaded_by FROM payment_batches WHERE batch_id = ?",
        (req.batch_id,),
    )
    _b = cur.fetchone()
    uploader = None
    if _b is not None and "uploaded_by" in _b.keys():
        uploader = _b["uploaded_by"]
​
    cur.execute(
        """
        INSERT INTO notifications
            (batch_id, recipient_role, recipient_user, notification_type, title, message, decision)
        VALUES (?, 'ap', ?, 'DECISION', ?, ?, ?)
        """,
        (
            req.batch_id,
            uploader,
            f"Batch {nice} by CFO",
            f"Batch {req.file_name} was {nice} by the CFO",
            req.decision,
        ),
    )
​
    conn.commit()
    conn.close()
​
    # Best-effort real-time push (in addition to the DB notification above).
    # Wrapped so a websocket hiccup never fails the decision request.
    try:
        await manager.notify_role(
            "ap",
            {
                "type": req.decision,
                "batch_id": req.batch_id,
                "file_name": req.file_name,
                "message": f"Batch {nice} by CFO",
            },
        )
    except Exception:
        pass
​
    return {
        "success": True
    }
​
​
@router.get("/decision-history")
def get_history():
​
    conn = get_db_connection()
    cur = conn.cursor()
​
    cur.execute(
        """
        SELECT
            batch_id,
            file_name,
            decision,
            decided_by,
            decided_at,
            comment
        FROM batch_decision_history
        ORDER BY decided_at DESC
        LIMIT 7
        """
    )
​
    rows = [dict(r) for r in cur.fetchall()]
​
    conn.close()
​
    return {
        "success": True,
        "data": rows
    }
​
​
# ---------------------------------------------------
# NOTIFICATIONS FEED
# GET /notifications?role=cfo|ap  -> recent notifications for that role
# POST /notifications/{id}/read   -> mark one as read
# ---------------------------------------------------
@router.get("/notifications")
def get_notifications(role: str, user: str = None):
​
    conn = get_db_connection()
    cur = conn.cursor()
​
    # AP users only see notifications addressed to them specifically
    # (recipient_user). Older/un-targeted rows (NULL) stay visible to all AP
    # so nothing silently disappears. CFO stays role-based.
    if role == "ap" and user:
        cur.execute(
            """
            SELECT
                notification_id,
                batch_id,
                notification_type,
                title,
                message,
                decision,
                is_read,
                created_at
            FROM notifications
            WHERE recipient_role = 'ap'
              AND (recipient_user = ? OR recipient_user IS NULL)
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (user,),
        )
    else:
        cur.execute(
            """
            SELECT
                notification_id,
                batch_id,
                notification_type,
                title,
                message,
                decision,
                is_read,
                created_at
            FROM notifications
            WHERE recipient_role = ?
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (role,),
        )
​
    rows = [dict(r) for r in cur.fetchall()]
​
    conn.close()
​
    return {
        "success": True,
        "data": rows
    }
​
​
@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int):
​
    conn = get_db_connection()
    cur = conn.cursor()
​
    cur.execute(
        "UPDATE notifications SET is_read = 1 WHERE notification_id = ?",
        (notification_id,),
    )
​
    conn.commit()
    conn.close()
​
    return {
        "success": True
    }
​