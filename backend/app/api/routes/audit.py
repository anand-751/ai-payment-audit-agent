from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.services.validation_service import (
    validate_payment_batch
)

from app.services.pdf_service import (
    generate_batch_pdf
)

router = APIRouter()


@router.post("/run-audit/{batch_id}")
async def run_audit(batch_id: str):

    try:

        result = validate_payment_batch(batch_id)

        return {
            "success": True,
            "message": "Audit completed successfully.",
            "data": result
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/export-log/{batch_id}")
async def export_log(batch_id: str):

    try:

        pdf_path = generate_batch_pdf(batch_id)

        print(f"PDF GENERATED: {pdf_path}")

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"{batch_id}.pdf",
        )

    except FileNotFoundError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception as e:

        print("EXPORT ERROR:", str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )