from sqlalchemy import Column, Integer, String, Text, Boolean, Date, Time, DateTime, SmallInteger, Numeric, ForeignKey, Enum as SQLEnum, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class JobStatus(str, enum.Enum):
    applied = "applied"
    interviewing = "interviewing"
    rejected = "rejected"
    no_response = "no response"
    saved = "saved"


class ContactTitle(str, enum.Enum):
    recruiter = "recruiter"
    hiring_manager = "hiring manager"
    hr = "hr"
    engineer = "engineer"
    vp = "vp"
    other = "other"


class AppointmentType(str, enum.Enum):
    phone_call = "phone call"
    interview = "interview"
    on_site = "on site"
    technical = "technical"


class CommunicationType(str, enum.Enum):
    phone = "phone"
    email = "email"
    sms = "sms"
    message = "message"


class FileFormat(str, enum.Enum):
    pdf = "pdf"
    odt = "odt"
    md = "md"
    html = "html"
    docx = "docx"


class Resume(Base):
    __tablename__ = "resume"

    resume_id = Column(Integer, primary_key=True, index=True)
    baseline_resume_id = Column(Integer, ForeignKey("resume.resume_id", ondelete="RESTRICT"))
    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="SET NULL"))
    original_format = Column(SQLEnum(FileFormat), nullable=False)
    resume_title = Column(String(128), nullable=False)
    file_name = Column(String(128), unique=True)
    is_baseline = Column(Boolean, default=False, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    resume_created = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    resume_updated = Column(DateTime(timezone=False))

    # Relationships
    jobs = relationship("Job", back_populates="resume", foreign_keys="[Job.resume_id]")
    baseline_resume = relationship("Resume", remote_side=[resume_id], foreign_keys=[baseline_resume_id])
    job = relationship("Job", foreign_keys=[job_id])
    detail = relationship("ResumeDetail", back_populates="resume", uselist=False)


class ResumeDetail(Base):
    __tablename__ = "resume_detail"

    resume_id = Column(Integer, ForeignKey("resume.resume_id", ondelete="CASCADE"), primary_key=True)
    resume_markdown = Column(Text)
    resume_md_rewrite = Column(Text)
    resume_html = Column(Text)
    resume_html_rewrite = Column(Text)
    position_title = Column(String(128))
    title_line_no = Column(SmallInteger)
    keyword_count = Column(SmallInteger)
    resume_keyword = Column(ARRAY(String(128)))
    keyword_final = Column(ARRAY(String(128)))
    focus_count = Column(SmallInteger)
    focus_final = Column(ARRAY(String(128)))
    baseline_score = Column(SmallInteger)
    rewrite_score = Column(SmallInteger)
    suggestion = Column(ARRAY(Text))
    rewrite_file_name = Column(String(128))

    # Relationships
    resume = relationship("Resume", back_populates="detail")


class LetterLength(str, enum.Enum):
    short = "short"
    medium = "medium"
    long = "long"


class LetterTone(str, enum.Enum):
    professional = "professional"
    casual = "casual"
    enthusiastic = "enthusiastic"
    informational = "informational"


class CoverLetter(Base):
    __tablename__ = "cover_letter"

    cover_id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resume.resume_id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), nullable=False)
    letter_length = Column(SQLEnum(LetterLength), default=LetterLength.medium, nullable=False)
    letter_tone = Column(SQLEnum(LetterTone), default=LetterTone.professional, nullable=False)
    instruction = Column(Text, nullable=False)
    letter_content = Column(Text, nullable=False)
    file_directory = Column(String(255))
    file_name = Column(String(128))
    cover_created = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    letter_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    jobs = relationship("Job", back_populates="cover_letter", foreign_keys="[Job.cover_id]")


class Job(Base):
    __tablename__ = "job"

    job_id = Column(Integer, primary_key=True, index=True)
    company = Column(String(64))
    job_title = Column(String(255))
    salary = Column(String(92))
    location = Column(String(128))
    interest_level = Column(SmallInteger, default=1)
    average_score = Column(Numeric(4, 3), nullable=False, default=5)
    posting_url = Column(Text)
    apply_url = Column(Text)
    job_status = Column(SQLEnum(JobStatus, values_callable=lambda x: [e.value for e in x]), default=JobStatus.applied)
    date_applied = Column(Date)
    last_activity = Column(Date, server_default=func.current_date())
    job_active = Column(Boolean, default=True)
    resume_id = Column(Integer, ForeignKey("resume.resume_id", ondelete="SET NULL"))
    cover_id = Column(Integer, ForeignKey("cover_letter.cover_id", ondelete="SET NULL"))
    job_created = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    job_directory = Column(String(255))

    # Relationships
    resume = relationship("Resume", back_populates="jobs", foreign_keys=[resume_id])
    cover_letter = relationship("CoverLetter", back_populates="jobs", foreign_keys=[cover_id])
    contacts = relationship("JobContact", back_populates="job")
    notes = relationship("Note", back_populates="job")
    calendar_events = relationship("Calendar", back_populates="job")
    communications = relationship("Communication", back_populates="job")
    documents = relationship("Document", back_populates="job")
    detail = relationship("JobDetail", back_populates="job", uselist=False)


class JobDetail(Base):
    __tablename__ = "job_detail"

    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), primary_key=True)
    job_desc = Column(Text)
    job_qualification = Column(Text)
    job_keyword = Column(ARRAY(String(128)))

    # Relationships
    job = relationship("Job", back_populates="detail")


class Contact(Base):
    __tablename__ = "contact"

    contact_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(92))
    last_name = Column(String(92))
    job_title = Column(String(255))
    email = Column(String(255))
    phone = Column(String(24))
    company = Column(String(64))
    linkedin = Column(String(255))
    contact_note = Column(Text)
    contact_active = Column(Boolean, default=True)

    # Relationships
    jobs = relationship("JobContact", back_populates="contact")
    communications = relationship("Communication", back_populates="contact")


class JobContact(Base):
    __tablename__ = "job_contact"

    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), primary_key=True)
    contact_id = Column(Integer, ForeignKey("contact.contact_id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    job = relationship("Job", back_populates="contacts")
    contact = relationship("Contact", back_populates="jobs")


class Note(Base):
    __tablename__ = "note"

    note_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), nullable=False)
    note_title = Column(String(255))
    note_content = Column(Text)
    note_active = Column(Boolean, default=True)
    note_created = Column(DateTime(timezone=False), server_default=func.current_timestamp())

    # Relationships
    job = relationship("Job", back_populates="notes")


class Calendar(Base):
    __tablename__ = "calendar"

    calendar_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), nullable=False)
    calendar_type = Column(SQLEnum(AppointmentType), default=AppointmentType.interview)
    start_date = Column(Date)
    start_time = Column(Time)
    end_date = Column(Date)
    end_time = Column(Time)
    duration_hour = Column(Numeric(4, 2))
    participant = Column(ARRAY(String(192)))
    calendar_desc = Column(Text)
    calendar_note = Column(Text)
    outcome_score = Column(SmallInteger)
    outcome_note = Column(Text)
    video_link = Column(String(255))

    # Relationships
    job = relationship("Job", back_populates="calendar_events")


class Communication(Base):
    __tablename__ = "communication"

    communication_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact.contact_id", ondelete="CASCADE"))
    communication_type = Column(SQLEnum(CommunicationType), nullable=False)
    contact_person = Column(String(255))
    communication_note = Column(Text)

    # Relationships
    job = relationship("Job", back_populates="communications")
    contact = relationship("Contact", back_populates="communications")


class Document(Base):
    __tablename__ = "document"

    document_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String(255))
    document_desc = Column(Text)
    file_directory = Column(String(255))
    file_name = Column(String(128))
    document_added = Column(DateTime(timezone=False), server_default=func.current_timestamp())

    # Relationships
    job = relationship("Job", back_populates="documents")


class Personal(Base):
    __tablename__ = "personal"

    first_name = Column(String(92), primary_key=True)
    last_name = Column(String(92), primary_key=True)
    email = Column(String(255))
    phone = Column(String(24))
    linkedin_url = Column(String(255))
    github_url = Column(String(255))
    website_url = Column(String(255))
    portfolio_url = Column(String(255))
    address_1 = Column(String(255))
    address_2 = Column(String(255))
    city = Column(String(128))
    state = Column(String(64))
    zip = Column(String(16))
    country = Column(String(64))
    login = Column(String(64))
    passwd = Column(String(64))
    no_response_week = Column(SmallInteger)
    default_llm = Column(String(32))
    resume_extract_llm = Column(String(32))
    job_extract_llm = Column(String(32))
    rewrite_llm = Column(String(32))
    cover_llm = Column(String(32))
    company_llm = Column(String(32))
    tools_llm = Column(String(32))
    openai_api_key = Column(String(255))
    tinymce_api_key = Column(String(255))
    convertapi_key = Column(String(255))
    docx2html = Column(String(32))
    odt2html = Column(String(32))
    pdf2html = Column(String(32))
    html2docx = Column(String(32))
    html2odt = Column(String(32))
    html2pdf = Column(String(32))

class Process(Base):
	__tablename__ = "process"

	process_id = Column(Integer, primary_key=True, index=True)
	endpoint_called = Column(String(128))
	running_method = Column(String(64))
	running_class = Column(String(64))
	started = Column(DateTime(timezone=False), server_default=func.current_timestamp())
	completed = Column(DateTime(timezone=False))
	confirmed = Column(Boolean, default=False, nullable=False)
	failed = Column(Boolean, default=False, nullable=False)


class Company(Base):
	__tablename__ = "company"

	company_id = Column(Integer, primary_key=True, index=True)
	company_name = Column(String(128), nullable=False)
	website_url = Column(String(255))
	hq_city = Column(String(128))
	hq_state = Column(String(128))
	industry = Column(String(128))
	logo_file = Column(String(128))
	linkedin_url = Column(String(255))
	job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"))
	report_html = Column(Text)
	report_created = Column(DateTime(timezone=False))
	company_created = Column(DateTime(timezone=False), server_default=func.current_timestamp())

	# Relationships
	job = relationship("Job", foreign_keys=[job_id])


