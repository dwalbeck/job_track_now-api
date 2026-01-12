from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class ToolsPitchRequest(BaseModel):
    job_id: Optional[int] = None

class ToolsPitchResponse(BaseModel):
    pitch: str

class ToolsRewriteRequest(BaseModel):
    text_blob: str

class ToolsRewriteResponse(BaseModel):
    original_text_blob: str
    new_text_blob: str
    explanation: str
