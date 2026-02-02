from typing import Optional, List
from datetime import date, datetime, time
from pydantic import BaseModel, field_validator
from ..models.models import JobStatus


class JobBase(BaseModel):
    company: str
    job_title: str
    salary: Optional[str] = None
    location: Optional[str] = None
    interest_level: int = 1
    posting_url: Optional[str] = None
    apply_url: Optional[str] = None
    job_status: JobStatus
    date_applied: Optional[date] = None
    average_score: Optional[float] = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    job_id: Optional[int] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    interest_level: Optional[int] = None
    posting_url: Optional[str] = None
    apply_url: Optional[str] = None
    job_status: Optional[JobStatus] = None
    date_applied: Optional[date] = None
    average_score: Optional[float] = None
    job_desc: Optional[str] = None

    @field_validator('job_id', 'interest_level', mode='before')
    @classmethod
    def empty_str_to_none_int(cls, v):
        if v == '':
            return None
        return v

    @field_validator('company', 'job_title', 'salary', 'location', 'posting_url', 'apply_url', 'job_desc', mode='before')
    @classmethod
    def empty_str_to_none_str(cls, v):
        if v == '':
            return None
        return v

    @field_validator('job_status', mode='before')
    @classmethod
    def empty_str_to_none_or_enum(cls, v):
        if v == '':
            return None
        return v


class Job(JobBase):
    job_id: int
    resume_id: Optional[int] = None
    cover_id: Optional[int] = None
    job_created: datetime
    job_directory: Optional[str] = None
    last_activity: Optional[date] = None
    # Calendar fields from latest appointment
    calendar_id: Optional[int] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    class Config:
        from_attributes = True


class JobList(BaseModel):
    job_id: int
    company: str
    job_title: str

    class Config:
        from_attributes = True


# JobDetail schemas
class JobDetailBase(BaseModel):
    job_id: int
    job_desc: Optional[str] = None
    job_qualification: Optional[str] = None
    job_keyword: Optional[List[str]] = None


class JobDetailCreate(JobDetailBase):
    pass


class JobDetail(JobDetailBase):
    class Config:
        from_attributes = True


# Job extraction request/response schemas
class JobExtractRequest(BaseModel):
    job_id: int


class JobExtractResponse(BaseModel):
    job_qualification: str
    keywords: List[str]