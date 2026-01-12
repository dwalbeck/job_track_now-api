import re
from typing import Optional
from pydantic import BaseModel, field_validator


class PersonalBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    no_response_week: Optional[int] = None
    resume_extract_llm: Optional[str] = None
    job_extract_llm: Optional[str] = None
    rewrite_llm: Optional[str] = None
    cover_llm: Optional[str] = None
    company_llm: Optional[str] = None
    openai_api_key: Optional[str] = None
    tinymce_api_key: Optional[str] = None
    convertapi_key: Optional[str] = None
    docx2html: Optional[str] = None
    odt2html: Optional[str] = None
    pdf2html: Optional[str] = None
    html2docx: Optional[str] = None
    html2odt: Optional[str] = None
    html2pdf: Optional[str] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and v.strip():
            # Basic email validation
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, v):
                raise ValueError('Invalid email format')
        return v

    @field_validator('linkedin_url', 'github_url', 'website_url', 'portfolio_url')
    @classmethod
    def validate_url(cls, v):
        if v and v.strip():
            # Basic URL validation
            if not v.startswith(('http://', 'https://')):
                raise ValueError('URL must start with http:// or https://')
        return v


class PersonalCreate(PersonalBase):
    pass


class PersonalUpdate(PersonalBase):
    pass


class Personal(PersonalBase):
    class Config:
        from_attributes = True
