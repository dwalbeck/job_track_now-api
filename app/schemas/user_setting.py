from typing import Optional
from pydantic import BaseModel


class UserSettingRequest(BaseModel):
    """Schema for user setting create/update request"""
    user_id: int
    no_response_week: Optional[int] = None
    docx2html: Optional[str] = None
    odt2html: Optional[str] = None
    pdf2html: Optional[str] = None
    html2docx: Optional[str] = None
    html2odt: Optional[str] = None
    html2pdf: Optional[str] = None
    default_llm: Optional[str] = None
    resume_extract_llm: Optional[str] = None
    job_extract_llm: Optional[str] = None
    rewrite_llm: Optional[str] = None
    cover_llm: Optional[str] = None
    company_llm: Optional[str] = None
    tools_llm: Optional[str] = None
    culture_llm: Optional[str] = None
    question_llm: Optional[str] = None
    stt_llm: Optional[str] = None
    openai_api_key: Optional[str] = None
    tinymce_api_key: Optional[str] = None
    convertapi_key: Optional[str] = None


class UserSettingResponse(BaseModel):
    """Schema for user setting response"""
    user_id: int
    no_response_week: Optional[int] = None
    docx2html: Optional[str] = None
    odt2html: Optional[str] = None
    pdf2html: Optional[str] = None
    html2docx: Optional[str] = None
    html2odt: Optional[str] = None
    html2pdf: Optional[str] = None
    default_llm: Optional[str] = None
    resume_extract_llm: Optional[str] = None
    job_extract_llm: Optional[str] = None
    rewrite_llm: Optional[str] = None
    cover_llm: Optional[str] = None
    company_llm: Optional[str] = None
    tools_llm: Optional[str] = None
    culture_llm: Optional[str] = None
    question_llm: Optional[str] = None
    stt_llm: Optional[str] = None
    openai_api_key: Optional[str] = None
    tinymce_api_key: Optional[str] = None
    convertapi_key: Optional[str] = None

    class Config:
        from_attributes = True
