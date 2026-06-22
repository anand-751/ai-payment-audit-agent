import os
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)

from app.core.database import get_db_connection

EXPORT_DIR = "exports"


def _safe_str(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def _make_long_table(headers, rows, available_width, header_style, body_style):
    """
    Build a wide, multi-page table that can contain all columns and split
    naturally across pages.
    """
    if not headers:
        return None

    data = [[Paragraph(_safe_str(h), header_style) for h in headers]]

    for row in rows:
        data.append([
            Paragraph(_safe_str(row.get(h, "")), body_style) for h in headers
        ])

    col_widths = [available_width / max(len(headers), 1)] * len(headers)

    table = LongTable(
        data,
        colWidths=col_widths,
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#444444")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    return table


def _build_summary_table(batch_dict, file_name, available_width, header_style, body_style):
    """
    Small executive summary table for the CFO.
    Uses whatever batch fields exist in payment_batches.
    """
    summary_fields = [
        ("Batch ID", batch_dict.get("batch_id", "")),
        ("File", file_name),
        ("Batch Status", batch_dict.get("batch_status", "")),
        ("Total Items", batch_dict.get("total_items", "")),
        ("Total Amount", batch_dict.get("total_amount", "")),
        ("Uploaded At", batch_dict.get("uploaded_at", "")),
        ("File Path", batch_dict.get("file_path", "")),
    ]

    data = [
        [
            Paragraph("<b>Field</b>", header_style),
            Paragraph("<b>Value</b>", header_style),
        ]
    ]

    for label, value in summary_fields:
        data.append([
            Paragraph(_safe_str(label), body_style),
            Paragraph(_safe_str(value), body_style),
        ])

    table = LongTable(
        data,
        colWidths=[available_width * 0.28, available_width * 0.72],
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#444444")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    return table


def generate_batch_pdf(batch_id: str):
    conn = get_db_connection()

    try:
        batch = conn.execute(
            """
            SELECT *
            FROM payment_batches
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()

        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch_dict = dict(batch)
        file_path = batch_dict.get("file_path")

        if not file_path:
            raise ValueError(f"file_path is missing for batch {batch_id}")

        audit_rows = conn.execute(
            """
            SELECT *
            FROM audit_results
            WHERE batch_id = ?
            ORDER BY payment_id
            """,
            (batch_id,),
        ).fetchall()

    finally:
        conn.close()

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Original file not found: {file_path}")

    os.makedirs(EXPORT_DIR, exist_ok=True)

    pdf_path = os.path.join(EXPORT_DIR, f"{batch_id}.pdf")

    # Reuse existing PDF if already generated
    if os.path.exists(pdf_path):
        return pdf_path

    df = pd.read_csv(file_path)

    pagesize = landscape(A4)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=pagesize,
        leftMargin=18,
        rightMargin=18,
        topMargin=18,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCenter",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=8,
    )

    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        spaceBefore=8,
        spaceAfter=8,
    )

    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        spaceAfter=2,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=7,
        alignment=1,
        wordWrap="CJK",
    )

    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6,
        leading=7,
        wordWrap="CJK",
    )

    elements = []

    # ---------------------------------------------------
    # Cover / Summary
    # ---------------------------------------------------
    elements.append(Paragraph("PAYMENT AUDIT REPORT", title_style))
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(f"<b>Batch ID:</b> {_safe_str(batch_dict.get('batch_id', batch_id))}", meta_style)
    )
    elements.append(
        Paragraph(f"<b>File:</b> {_safe_str(os.path.basename(file_path))}", meta_style)
    )
    elements.append(Spacer(1, 10))

    available_width = pagesize[0] - doc.leftMargin - doc.rightMargin

    elements.append(Paragraph("Batch Summary", section_style))
    elements.append(
        _build_summary_table(
            batch_dict=batch_dict,
            file_name=os.path.basename(file_path),
            available_width=available_width,
            header_style=table_header_style,
            body_style=table_body_style,
        )
    )

    elements.append(Spacer(1, 12))

    # ---------------------------------------------------
    # Original CSV Data
    # ---------------------------------------------------
    elements.append(PageBreak())
    elements.append(Paragraph("Original Payment Data", section_style))

    if not df.empty:
        # Keep all columns and all rows, split across pages automatically.
        df = df.where(pd.notnull(df), "")

        headers = list(df.columns)
        rows = df.to_dict(orient="records")

        original_table = _make_long_table(
            headers=headers,
            rows=rows,
            available_width=available_width,
            header_style=table_header_style,
            body_style=table_body_style,
        )

        elements.append(original_table)
    else:
        elements.append(Paragraph("No payment rows found in CSV.", meta_style))

    # ---------------------------------------------------
    # Audit Findings
    # ---------------------------------------------------
    elements.append(PageBreak())
    elements.append(Paragraph("Audit Findings", section_style))

    if audit_rows:
        audit_dicts = [dict(row) for row in audit_rows]
        audit_headers = list(audit_dicts[0].keys())

        audit_table = _make_long_table(
            headers=audit_headers,
            rows=audit_dicts,
            available_width=available_width,
            header_style=table_header_style,
            body_style=table_body_style,
        )
        elements.append(audit_table)
    else:
        elements.append(Paragraph("No violations found.", meta_style))

    doc.build(elements)
    return pdf_path