from fastapi import APIRouter
from pydantic import BaseModel

from app.core.database import get_db_connection
from app.services.websocket_manager import manager

router = APIRouter()


class DecisionRequest(BaseModel):
    batch_id: str
    file_name: str
    decision: str
    comment: str = ""


@router.post("/batch-decision")
async def save_decision(req: DecisionRequest):
    conn = get_db_connection()
    cur = conn.cursor()

    # Update batch status
    cur.execute(
        """
        UPDATE payment_batches
        SET batch_status = ?
        WHERE batch_id = ?
        """,
        (
            req.decision,
            req.batch_id,
        ),
    )

    # Insert decision history
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
            req.comment,
        ),
    )

    conn.commit()
    conn.close()

    # Notify AP Manager when CFO rejects a batch
    if req.decision == "REJECTED":
        await manager.notify_role(
            "ap",
            {
                "type": "REJECTED",
                "batch_id": req.batch_id,
                "file_name": req.file_name,
                "message": "Rejected by CFO",
            },
        )

    return {
        "success": True,
    }


@router.get("/decision-history")
def get_history():
    conn = get_db_connection()
    cur = conn.cursor()

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

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {
        "success": True,
        "data": rows,
    }