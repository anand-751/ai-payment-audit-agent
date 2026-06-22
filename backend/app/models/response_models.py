from pydantic import BaseModel
from typing import Any


class ResponseModel(BaseModel):
    success: bool
    data: Any = None
    message: str = ""
