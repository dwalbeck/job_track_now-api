from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class CompanyBase(BaseModel):
    company_name: str
    website_url: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    industry: Optional[str] = None
    linkedin_url: Optional[str] = None
    job_id: Optional[int] = None


class CompanyCreate(CompanyBase):
    @field_validator('website_url', 'hq_city', 'hq_state', 'industry', 'linkedin_url', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

    @field_validator('job_id', mode='before')
    @classmethod
    def empty_str_to_none_int(cls, v):
        if v == '':
            return None
        return v


class CompanyUpdate(BaseModel):
    company_id: int
    company_name: Optional[str] = None
    website_url: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    industry: Optional[str] = None
    linkedin_url: Optional[str] = None
    job_id: Optional[int] = None
    logo_file: Optional[str] = None
    company_logo_url: Optional[str] = None
    report_html: Optional[str] = None

    @field_validator('company_name', 'website_url', 'hq_city', 'hq_state', 'industry', 'linkedin_url', 'logo_file', 'company_logo_url', 'report_html', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

    @field_validator('company_id', 'job_id', mode='before')
    @classmethod
    def empty_str_to_none_int(cls, v):
        if v == '':
            return None
        return v


class CompanyResponse(BaseModel):
    company_id: int
    company_name: str
    website_url: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    industry: Optional[str] = None
    linkedin_url: Optional[str] = None
    job_id: Optional[int] = None
    logo_file: Optional[str] = None
    report_html: Optional[str] = None
    company_created: Optional[datetime] = None
    report_created: Optional[datetime] = None

    class Config:
        from_attributes = True
