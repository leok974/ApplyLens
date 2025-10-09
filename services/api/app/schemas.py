from pydantic import BaseModel
from datetime import datetime

class EmailOut(BaseModel):
    id: int
    thread_id: str
    from_addr: str
    subject: str
    label: str
    received_at: datetime

    class Config:
        from_attributes = True
