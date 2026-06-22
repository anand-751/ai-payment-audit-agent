import sqlite3
from pathlib import Path
from app.services.websocket_manager import manager
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Database path relative to project structure
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "payment_audit.db"


class DecisionRequest(BaseModel):
    batch_id: str
    file_name: str
    decision: str
    comment: str = ""

@router.post("/batch-decision")
async def save_decision(req: DecisionRequest):

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

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

    # insert history

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

    conn.commit()
    conn.close()

    if req.decision == "REJECTED":

        await manager.notify_role(
            "ap",
            {
                "type": "REJECTED",
                "batch_id": req.batch_id,
                "file_name": req.file_name,
                "message": "Rejected by CFO"
            }
        )  

    return {
        "success": True
    }


@router.get("/decision-history")
def get_history():

    conn = sqlite3.connect(str(DB_PATH))

    conn.row_factory = sqlite3.Row

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

    rows = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        "success": True,
        "data": rows
    }