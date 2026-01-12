from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class NoteBase(BaseModel):
    job_id: int
    note_title: Optional[str] = None
    note_content: Optional[str] = None


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    note_id: Optional[int] = None
    job_id: Optional[int] = None
    note_title: Optional[str] = None
    note_content: Optional[str] = None

    @field_validator('note_id', 'job_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class Note(NoteBase):
    note_id: int
    note_created: datetime
    job_title: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True