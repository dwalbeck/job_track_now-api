from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, field_validator


class ProcessBase(BaseModel):
    process_id: Optional[int] = None
    endpoint_called: Optional[str] = None
    running_method: Optional[str] = None
    running_class: Optional[str] = None
    started: Optional[date] = None
    completed: Optional[date] = None
    confirmed: Optional[bool] = None
    failed: Optional[bool] = None

class PollResponse(BaseModel):
    process_state: str

