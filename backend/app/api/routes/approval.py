from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.database import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/approval")


class DecisionRequest(BaseModel):
    decision: str
    comment: str = ""


@router.post("/batch/{batch_id}/decision")
async def submit_decision(batch_id: str, request: DecisionRequest, db=Depends(get_db)):
    """
    CFO submits decision on a batch
    decision: "APPROVED" or "REJECTED"
    """
    decision = request.decision
    comment = request.comment
    
    if decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid decision")
    
    try:
        cursor = db.cursor()
        
        # Update batch status
        cursor.execute(
            "UPDATE payment_batches SET batch_status = ?, cfo_comment = ? WHERE batch_id = ?",
            (decision, comment, batch_id)
        )
        
        # Create notification for AP Manager (rejections only)
        if decision == "REJECTED":
            # Look up who uploaded this batch so only that user is notified
            cursor.execute(
                "SELECT uploaded_by FROM payment_batches WHERE batch_id = ?",
                (batch_id,)
            )
            owner_row = cursor.fetchone()
            target_user = owner_row[0] if owner_row else None

            notification_type = "REJECTED"
            title = "Batch Rejected"
            message = f"Batch {batch_id} was rejected by CFO."
            if comment:
                message += f" Reason: {comment}"
            
            cursor.execute(
                """INSERT INTO notifications 
                   (batch_id, recipient_role, recipient_user, notification_type, title, message, decision)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (batch_id, "AP_MANAGER", target_user, notification_type, title, message, decision)
            )
        
        db.commit()
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "decision": decision,
            "message": "Decision recorded"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Decision submission error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_notification_history(role: str = "AP_MANAGER", user: str = None, limit: int = 7, db=Depends(get_db)):
    """
    Fetch historical notifications for a role
    Called only on demand when user clicks History button
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            """SELECT 
                notification_id, batch_id, notification_type, title, 
                message, decision, is_read, created_at
               FROM notifications 
               WHERE recipient_role = ?
                 AND (recipient_user = ? OR recipient_user IS NULL)
               ORDER BY created_at DESC
               LIMIT ?""",
            (role, user, limit)
        )
        
        rows = cursor.fetchall()
        notifications = []
        for row in rows:
            notifications.append({
                "id": row[0],
                "batchNo": row[1],
                "type": row[2],
                "title": row[3],
                "message": row[4],
                "decision": row[5],
                "is_read": row[6],
                "createdAt": row[7]
            })
        
        return {"notifications": notifications}
    except Exception as e:
        logger.error(f"History fetch error: {str(e)}")
        # Return empty list if table doesn't exist yet
        return {"notifications": []}


@router.get("/notifications")
async def get_active_notifications(role: str = "AP_MANAGER", user: str = None, db=Depends(get_db)):
    """
    Live notification feed.
    Shows ONLY unread (latest) notifications. Once a notification is marked
    read, it drops out of this feed. Previously read items remain available
    via the /history endpoint (view history).
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            """SELECT 
                notification_id, batch_id, notification_type, title, 
                message, decision, is_read, created_at
               FROM notifications 
               WHERE recipient_role = ?
                 AND (recipient_user = ? OR recipient_user IS NULL)
                 AND is_read = 0
               ORDER BY created_at DESC""",
            (role, user)
        )
        
        rows = cursor.fetchall()
        notifications = []
        for row in rows:
            notifications.append({
                "id": row[0],
                "batchNo": row[1],
                "type": row[2],
                "title": row[3],
                "message": row[4],
                "decision": row[5],
                "is_read": row[6],
                "createdAt": row[7]
            })
        
        return {"notifications": notifications}
    except Exception as e:
        logger.error(f"Active notifications fetch error: {str(e)}")
        # Return empty list if table doesn't exist yet
        return {"notifications": []}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, db=Depends(get_db)):
    """
    Mark a notification as read
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE notifications SET is_read = 1 WHERE notification_id = ?",
            (notification_id,)
        )
        db.commit()
        
        return {"status": "success", "notification_id": notification_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Mark read error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
