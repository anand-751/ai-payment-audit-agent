from fastapi import APIRouter

router = APIRouter(prefix="/reports")


@router.get("/")
async def get_reports():
    return {"reports": []}
