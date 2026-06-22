from pydantic import BaseModel
from typing import Optional


class Payment(BaseModel):
    id: Optional[int]
    vendor: str
    amount: float
    date: str
    status: Optional[str] = "pending"
