from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class LetterBase(BaseModel):
    resume_id: int
    job_id: int
    letter_length: str
    letter_tone: str
    instruction: str
    letter_content: str
    file_name: Optional[str] = None


class LetterCreate(LetterBase):
    pass


class LetterUpdate(LetterBase):
    cover_id: int


class Letter(LetterBase):
    cover_id: int
    letter_created: Optional[datetime] = None

    class Config:
        from_attributes = True


class LetterListItem(BaseModel):
    letter_length: str
    letter_tone: str
    file_name: Optional[str] = None
    letter_created: Optional[datetime] = None
    cover_id: int
    job_id: int
    resume_id: int
    company: Optional[str] = None
    job_title: Optional[str] = None

    class Config:
        from_attributes = True
