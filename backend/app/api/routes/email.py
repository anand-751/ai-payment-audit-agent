from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import sqlite3
from dotenv import load_dotenv
import os
import json
import base64
import urllib.request
import urllib.error
from app.core.config import settings

load_dotenv()

router = APIRouter()

DB_PATH = settings.DB_PATH
SMTP_EMAIL = settings.SMTP_EMAIL          # used as the verified "from" sender
RECIPIENT_EMAIL = settings.RECIPIENT_EMAIL

# SendGrid HTTP API (works on Railway because it uses HTTPS / port 443).
# Add SENDGRID_API_KEY in Railway -> Variables.
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"

print("DB_PATH =", DB_PATH)


class EmailRequest(BaseModel):
    batch_id: str
    comment: str


def _send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    attachment_bytes: bytes,
    attachment_name: str,
) -> None:
    """Sends the email via SendGrid's HTTP API in the background (no SMTP, no 504)."""
    if not SENDGRID_API_KEY:
        print("[email] FAILED: SENDGRID_API_KEY is not set")
        return

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": SMTP_EMAIL},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
        "attachments": [
            {
                "content": base64.b64encode(attachment_bytes).decode(),
                "filename": attachment_name,
                "type": "text/csv",
                "disposition": "attachment",
            }
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SENDGRID_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"[email] Sent to {to_email} (status {resp.status})")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[email] FAILED: HTTP {e.code} - {body}")
    except Exception as e:
        print(f"[email] FAILED: {e!r}")


@router.post("/authorize-disbursement")
def authorize(req: EmailRequest, background_tasks: BackgroundTasks):

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM payment_batches
        WHERE batch_id = ?
        """,
        (req.batch_id,)
    )

    batch = cur.fetchone()
    conn.close()

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Batch not found"
        )

    batch = dict(batch)
    file_path = batch.get("file_path")

    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="CSV file path not found."
        )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"CSV file not found: {file_path}"
        )

    file_name = os.path.basename(file_path)

    if "_" in file_name:
        file_name = file_name.split("_", 1)[1]

    subject = f"Payment Batch Approved - {file_name}"

    # --------------------------------------------------
    # Plain Text Fallback
    # --------------------------------------------------
    text_body = f"""
Payment Batch Authorized

Batch ID:
{req.batch_id}

File:
{file_name}

Status:
APPROVED FOR DISBURSEMENT

Approved By:
James Walker (CFO)

Comments:
{req.comment}
"""

    # --------------------------------------------------
    # Beautiful HTML Email
    # --------------------------------------------------
    html_body = f"""
<html>
<body style="
    background:#f4f6f9;
    padding:30px;
    font-family:Arial,Helvetica,sans-serif;
">
<div style="
    max-width:800px;
    margin:auto;
    background:#ffffff;
    border-radius:12px;
    overflow:hidden;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
">
    <div style="
        background:#0f172a;
        color:white;
        padding:24px;
    ">
        <h2 style="margin:0;">
            Payment Batch Authorized
        </h2>
        <p style="
            margin-top:8px;
            color:#cbd5e1;
        ">
            CFO Approval Notification
        </p>
    </div>
    <div style="padding:28px;">
        <h3>
            Batch Summary
        </h3>
        <table style="
            width:100%;
            border-collapse:collapse;
        ">
            <tr>
                <td style="
                    padding:12px;
                    font-weight:bold;
                    border-bottom:1px solid #eee;
                ">
                    Batch ID
                </td>
                <td style="
                    padding:12px;
                    border-bottom:1px solid #eee;
                ">
                    {req.batch_id}
                </td>
            </tr>
            <tr>
                <td style="
                    padding:12px;
                    font-weight:bold;
                    border-bottom:1px solid #eee;
                ">
                    Uploaded File
                </td>
                <td style="
                    padding:12px;
                    border-bottom:1px solid #eee;
                ">
                    📄 {file_name}
                </td>
            </tr>
            <tr>
                <td style="
                    padding:12px;
                    font-weight:bold;
                    border-bottom:1px solid #eee;
                ">
                    Status
                </td>
                <td style="
                    padding:12px;
                    color:#16a34a;
                    font-weight:bold;
                    border-bottom:1px solid #eee;
                ">
                    APPROVED FOR DISBURSEMENT
                </td>
            </tr>
            <tr>
                <td style="
                    padding:12px;
                    font-weight:bold;
                    border-bottom:1px solid #eee;
                ">
                    Approved By
                </td>
                <td style="
                    padding:12px;
                    border-bottom:1px solid #eee;
                ">
                    James Walker (CFO)
                </td>
            </tr>
        </table>
        <div style="
            margin-top:24px;
            padding:18px;
            background:#f8fafc;
            border-left:4px solid #16a34a;
            border-radius:6px;
        ">
            <div style="
                font-weight:bold;
                margin-bottom:8px;
            ">
                CFO Comments
            </div>
            <div>
                {req.comment if req.comment else "No comments provided."}
            </div>
        </div>
        <div style="
            margin-top:24px;
            padding:16px;
            background:#ecfeff;
            border:1px solid #a5f3fc;
            border-radius:8px;
        ">
            <b>Attached File:</b><br>
            {file_name}
        </div>
    </div>
    <div style="
        background:#f8fafc;
        padding:16px 24px;
        font-size:12px;
        color:#64748b;
    ">
        Generated automatically by Payment Audit Agent
    </div>
</div>
</body>
</html>
"""

    # --------------------------------------------------
    # Read CSV attachment
    # --------------------------------------------------
    with open(file_path, "rb") as f:
        attachment_bytes = f.read()

    # --------------------------------------------------
    # Queue Email (runs AFTER the response is sent -> no 504)
    # --------------------------------------------------
    background_tasks.add_task(
        _send_email,
        RECIPIENT_EMAIL,
        subject,
        text_body,
        html_body,
        attachment_bytes,
        file_name,
    )

    return {
        "success": True,
        "message": "Authorization email queued successfully.",
        "batch_id": req.batch_id,
        "file_name": file_name
    }




# from fastapi import APIRouter, HTTPException, BackgroundTasks
# from pydantic import BaseModel
# import sqlite3
# from dotenv import load_dotenv
# import smtplib
# from email.message import EmailMessage
# import os
# from app.core.config import settings

# load_dotenv()

# SMTP_HOST = "smtp.gmail.com"
# SMTP_PORT = 465

# router = APIRouter()

# DB_PATH = settings.DB_PATH
# SMTP_EMAIL = settings.SMTP_EMAIL
# SMTP_PASSWORD = settings.SMTP_PASSWORD
# RECIPIENT_EMAIL = settings.RECIPIENT_EMAIL

# print("DB_PATH =", DB_PATH)


# class EmailRequest(BaseModel):
#     batch_id: str
#     comment: str

# def _send_email(msg: EmailMessage) -> None:
#     """Sends the email in the background so the HTTP request returns instantly (prevents 504)."""
#     try:
#         with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
#             smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
#             smtp.send_message(msg)
#             print(f"[email] Sent to {msg['To']}")
#     except smtplib.SMTPAuthenticationError:
#         print("[email] FAILED: Invalid Gmail App Password")
#     except Exception as e:
#         print(f"[email] FAILED: {e!r}")

# @router.post("/authorize-disbursement")
# def authorize(req: EmailRequest, background_tasks: BackgroundTasks):
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row

#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT *
#         FROM payment_batches
#         WHERE batch_id = ?
#         """,
#         (req.batch_id,)
#     )

#     batch = cur.fetchone()
#     conn.close()

#     if not batch:
#         raise HTTPException(
#             status_code=404,
#             detail="Batch not found"
#         )

#     batch = dict(batch)

#     file_path = batch.get("file_path")

#     if not file_path:
#         raise HTTPException(
#             status_code=400,
#             detail="CSV file path not found."
#         )

#     if not os.path.exists(file_path):
#         raise HTTPException(
#             status_code=404,
#             detail=f"CSV file not found: {file_path}"
#         )

#     file_name = os.path.basename(file_path)

#     if "_" in file_name:
#         file_name = file_name.split("_", 1)[1]

#     msg = EmailMessage()

#     msg["Subject"] = f"Payment Batch Approved - {file_name}"
#     msg["From"] = SMTP_EMAIL
#     msg["To"] = RECIPIENT_EMAIL

#     # --------------------------------------------------
#     # Plain Text Fallback
#     # --------------------------------------------------

#     msg.set_content(
#         f"""
# Payment Batch Authorized

# Batch ID:
# {req.batch_id}

# File:
# {file_name}

# Status:
# APPROVED FOR DISBURSEMENT

# Approved By:
# James Walker (CFO)

# Comments:
# {req.comment}
# """
#     )

#     # --------------------------------------------------
#     # Beautiful HTML Email
#     # --------------------------------------------------

#     msg.add_alternative(
#         f"""
# <html>
# <body style="
# background:#f4f6f9;
# padding:30px;
# font-family:Arial,Helvetica,sans-serif;
# ">

# <div style="
# max-width:800px;
# margin:auto;
# background:#ffffff;
# border-radius:12px;
# overflow:hidden;
# box-shadow:0 4px 12px rgba(0,0,0,0.08);
# ">

# <div style="
# background:#0f172a;
# color:white;
# padding:24px;
# ">
# <h2 style="margin:0;">
# Payment Batch Authorized
# </h2>

# <p style="
# margin-top:8px;
# color:#cbd5e1;
# ">
# CFO Approval Notification
# </p>
# </div>

# <div style="padding:28px;">

# <h3>
# Batch Summary
# </h3>

# <table style="
# width:100%;
# border-collapse:collapse;
# ">

# <tr>
# <td style="
# padding:12px;
# font-weight:bold;
# border-bottom:1px solid #eee;
# ">
# Batch ID
# </td>

# <td style="
# padding:12px;
# border-bottom:1px solid #eee;
# ">
# {req.batch_id}
# </td>
# </tr>

# <tr>
# <td style="
# padding:12px;
# font-weight:bold;
# border-bottom:1px solid #eee;
# ">
# Uploaded File
# </td>

# <td style="
# padding:12px;
# border-bottom:1px solid #eee;
# ">
# 📄 {file_name}
# </td>
# </tr>

# <tr>
# <td style="
# padding:12px;
# font-weight:bold;
# border-bottom:1px solid #eee;
# ">
# Status
# </td>

# <td style="
# padding:12px;
# color:#16a34a;
# font-weight:bold;
# border-bottom:1px solid #eee;
# ">
# APPROVED FOR DISBURSEMENT
# </td>
# </tr>

# <tr>
# <td style="
# padding:12px;
# font-weight:bold;
# border-bottom:1px solid #eee;
# ">
# Approved By
# </td>

# <td style="
# padding:12px;
# border-bottom:1px solid #eee;
# ">
# James Walker (CFO)
# </td>
# </tr>

# </table>

# <div style="
# margin-top:24px;
# padding:18px;
# background:#f8fafc;
# border-left:4px solid #16a34a;
# border-radius:6px;
# ">

# <div style="
# font-weight:bold;
# margin-bottom:8px;
# ">
# CFO Comments
# </div>

# <div>
# {req.comment if req.comment else "No comments provided."}
# </div>

# </div>

# <div style="
# margin-top:24px;
# padding:16px;
# background:#ecfeff;
# border:1px solid #a5f3fc;
# border-radius:8px;
# ">
# <b>Attached File:</b><br><br>
# {file_name}
# </div>

# </div>

# <div style="
# background:#f8fafc;
# padding:16px 24px;
# font-size:12px;
# color:#64748b;
# ">
# Generated automatically by Payment Audit Agent
# </div>

# </div>
# </body>
# </html>
# """,
#         subtype="html"
#     )

#     # --------------------------------------------------
#     # Attach CSV
#     # --------------------------------------------------

#     with open(file_path, "rb") as f:
#         msg.add_attachment(
#             f.read(),
#             maintype="text",
#             subtype="csv",
#             filename=file_name
#         )

#     # --------------------------------------------------
#     # Queue Email (runs AFTER response is sent)
#     # --------------------------------------------------

#     background_tasks.add_task(_send_email, msg)

#     return {
#         "success": True,
#         "message": "Authorization email queued successfully.",
#         "batch_id": req.batch_id,
#         "file_name": file_name
#     }
