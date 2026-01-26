from typing import Optional, List
from pydantic import BaseModel, field_validator


class ContactBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    linkedin: Optional[str] = None
    contact_note: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    contact_id: Optional[int] = None
    user_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    linkedin: Optional[str] = None
    contact_note: Optional[str] = None
    job_id: Optional[int] = None

    @field_validator('contact_id', 'job_id', 'user_id', mode='before')
    @classmethod
    def empty_str_to_none_int(cls, v):
        if v == '':
            return None
        return v

    @field_validator('first_name', 'last_name', 'job_title', 'email', 'phone', 'company', 'linkedin', 'contact_note', mode='before')
    @classmethod
    def empty_str_to_none_str(cls, v):
        if v == '':
            return None
        return v


class ContactLinkedJob(BaseModel):
    job_id: int
    job_title: str
    company: str

    class Config:
        from_attributes = True


class Contact(ContactBase):
    contact_id: int

    class Config:
        from_attributes = True


class ContactWithLinks(Contact):
    linked_to: List[ContactLinkedJob] = []