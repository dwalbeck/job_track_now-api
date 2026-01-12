from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from ..models.models import FileFormat


class ResumeBase(BaseModel):
    resume_title: str
    file_name: Optional[str] = None
    is_baseline: bool = False
    is_default: bool = False
    is_active: bool = True


class ResumeCreate(ResumeBase):
    baseline_resume_id: Optional[int] = None
    job_id: Optional[int] = None
    original_format: FileFormat


class ResumeUpdate(ResumeBase):
    resume_id: Optional[int] = None
    baseline_resume_id: Optional[int] = None
    job_id: Optional[int] = None
    original_format: Optional[FileFormat] = None


class Resume(ResumeBase):
    resume_id: int
    baseline_resume_id: Optional[int] = None
    job_id: Optional[int] = None
    original_format: FileFormat
    resume_created: datetime
    resume_updated: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumeDetailBase(BaseModel):
    resume_id: int
    resume_markdown: Optional[str] = None
    resume_md_rewrite: Optional[str] = None
    resume_html: Optional[str] = None
    resume_html_rewrite: Optional[str] = None
    position_title: Optional[str] = None
    title_line_no: Optional[int] = None
    keyword_count: Optional[int] = None
    resume_keyword: Optional[List[str]] = None
    focus_keyword: Optional[List[str]] = None
    keyword_final: Optional[List[str]] = None
    focus_count: Optional[int] = None
    focus_final: Optional[List[str]] = None
    baseline_score: Optional[int] = None
    rewrite_score: Optional[int] = None
    suggestion: Optional[List[str]] = None


class ResumeDetailCreate(ResumeDetailBase):
    pass


class ResumeDetail(ResumeDetailBase):
    class Config:
        from_attributes = True


class ResumeBaseline(BaseModel):
    resume_id: int
    resume_title: str
    resume_updated: Optional[datetime] = None
    is_default: bool
    keyword_count: Optional[int] = None
    focus_count: Optional[int] = None

    class Config:
        from_attributes = True


class ResumeBaselineList(BaseModel):
    resume_id: int
    resume_title: str
    is_default: bool

    class Config:
        from_attributes = True


class ResumeJob(BaseModel):
    resume_id: int
    resume_updated: Optional[datetime] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    keyword_count: Optional[int] = None
    focus_count: Optional[int] = None
    baseline_score: Optional[int] = None
    rewrite_score: Optional[int] = None
    job_id: Optional[int] = None
    baseline_resume_id: Optional[int] = None

    class Config:
        from_attributes = True


class ResumeCloneRequest(BaseModel):
    resume_id: int


class ResumeExtractRequest(BaseModel):
    resume_id: int

class ResumeExtractResponse(BaseModel):
    job_title: str
    suggestions: List[str]

class ResumeRewriteRequest(BaseModel):
    job_id: int

class ResumeRewriteResponse(BaseModel):
    resume_id: int
    resume_html: str
    resume_html_rewrite: str
    suggestion: List[str]
    baseline_score: int
    rewrite_score: int

class ResumeFullRequest(BaseModel):
    baseline_resume_id: int
    job_id: int
    keyword_final: List[str]
    focus_final: List[str]

class ResumeFullResponse(BaseModel):
    resume_id: int
