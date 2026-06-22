from pydantic import BaseModel


class AuditRecord(BaseModel):
    id: int
    action: str
    timestamp: str
    details: dict
