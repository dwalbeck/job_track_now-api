from typing import Optional, List
from datetime import date, time
from pydantic import BaseModel, field_validator


class CalendarBase(BaseModel):
    job_id: int
    calendar_type: str = "interview"
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    duration_hour: Optional[float] = None
    participant: Optional[List[str]] = []
    calendar_desc: Optional[str] = None
    calendar_note: Optional[str] = None
    outcome_score: Optional[int] = None
    outcome_note: Optional[str] = None
    video_link: Optional[str] = None


class CalendarCreate(CalendarBase):
    pass


class CalendarUpdate(BaseModel):
    calendar_id: Optional[int] = None
    job_id: Optional[int] = None
    calendar_type: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    duration_hour: Optional[float] = None
    participant: Optional[List[str]] = None
    calendar_desc: Optional[str] = None
    calendar_note: Optional[str] = None
    outcome_score: Optional[int] = None
    outcome_note: Optional[str] = None
    video_link: Optional[str] = None

    @field_validator('calendar_id', 'job_id', 'outcome_score', mode='before')
    @classmethod
    def empty_str_to_none_int(cls, v):
        if v == '':
            return None
        return v

    @field_validator('calendar_type', 'calendar_desc', 'calendar_note', 'outcome_note', 'video_link', mode='before')
    @classmethod
    def empty_str_to_none_str(cls, v):
        if v == '':
            return None
        return v

    @field_validator('duration_hour', mode='before')
    @classmethod
    def empty_str_to_none_float(cls, v):
        if v == '':
            return None
        return v


class Calendar(CalendarBase):
    calendar_id: int
    company: Optional[str] = None

    class Config:
        from_attributes = True