# Job Track Now - Backend API

A FastAPI-based backend service for the Job Tracker application, which is a complete tool for organizing 
job submissions, interview appointments, contacts, notes and will customize your resume based on the job 
posting information.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **PostgreSQL Database**: Robust relational database with SQLAlchemy ORM
- **RESTful API**: Complete CRUD operations for jobs, contacts, calendar, and notes
- **Automatic Documentation**: Interactive API docs at `/docs`
- **CORS Support**: Configured for frontend integration
- **Pydantic Validation**: Request/response validation and serialization
- **File Conversions**: Handles docx, odt, pdf, markdown and HTML formats
- **AI Agent Requests**: For performing resume rewrites, data extraction, and recommendations
- **Exportable Data**: All data can be exported

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Virtual environment (recommended)

### Installation

1. Create and activate virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   # Add OpenAI API key and project ID
   ```

4. Configure database:
   - Create PostgreSQL database named `jobtracker`
   - Run the **docs/schema.sql** file to create tables, create role and grant rights

### Running the Application

```bash
python run.py
```

The API will be available at:
- **API**: http://api.jobtracknow.com or http://localhost:8000
- **Documentation**: http://api.jobtracknow.com/docs or http://localhost:8000/docs

NOTE: it is important that you complete the "Personal" section by entering in your personal information upon 
first use, as it uses this information for file naming and cover letter creation. It also let's you customize 
how a few things will operate as well.


## API Endpoints

### Jobs
- `DELETE /v1/job/{job_id}` - Soft delete job
- `GET /v1/job/{job_id}` - Get single job
- `GET /v1/job/list` - Get job list for dropdowns
- `GET /v1/jobs` - Get list of all jobs
- `POST /v1/job` - Create or update job
- `POST /v1/job/extract` - Pulls job requirements and keywords
- `POST /v1/job/detail` - Create or update job_detail

### Contacts
- `POST /v1/contact` - Create or update contact
- `DELETE /v1/contact/{contact_id}` - Soft delete contact
- `GET /v1/contact/{contact_id}` - Get single contact with linked jobs
- `GET /v1/contacts` - Get all contacts (with optional job filter)

### Calendar
- `POST /v1/calendar` - Create or update appointment
- `GET /v1/calendar/month` - Get monthly appointments
- `GET /v1/calendar/week` - Get weekly appointments
- `GET /v1/calendar/day` - Get daily appointments
- `GET /v1/calendar/appt` - Get a calendar appointment
- `DELETE /v1/calendar/appt` - Remove a calendar appointment
- `POST /v1/reminder` - Create or update a reminder
- `DELETE /v1/reminder` - Remove a reminder
- `POST /v1/reminder/list` - Get a list of reminders for a time block

### Notes
- `GET /v1/notes` - Get all notes (with optional job filter)
- `POST /v1/notes` - Create or update note
- `DELETE /v1/note/{note_id}` - Soft delete note

### Conversions
- `POST /v1/convert/docx2md` - Convert docx file to markdown
- `POST /v1/convert/docx2html` - Convert docx file to HTML
- `POST /v1/convert/odt2md` - Convert odt file to markdown
- `POST /v1/convert/odt2html` - Convert odt file to HTML
- `POST /v1/convert/pdf2md` - Convert pdf file to markdown
- `POST /v1/convert/pdf2html` - Convert pdf file to HTML
- `POST /v1/convert/md2html` - Convert docx file to markdown
- `POST /v1/convert/final` - Convert the rewritten markdown to docx

### Exports
- `GET /v1/export/jobs` - Export jobs as CSV file
- `GET /v1/export/contacts` - Export contacts as CSV file
- `GET /v1/export/notes` - Export notes as CSV file
- `GET /v1/export/calendar` - Export calendar appointments as CSV file
- `GET /v1/export/resumes` - Export resumes as CSV file

### Cover Letter
- `GET /v1/letter` - Get a cover letter record
- `DELETE /v1/letter` - Remove a cover letter
- `POST /v1/letter` - Create or update a cover letter
- `GET /v1/letter/list` - Get a list of cover letters
- `GET /v1/letter/write` - Trigger writing a cover letter
- `GET /v1/letter/convert` - Convert cover letter to docx

### Resume
- `POST /v1/resume` - Create or update a resume
- `GET /v1/resume` - Get a resume record
- `DELETE /v1/resume` - Soft delete a resume
- `GET /v1/resume/baseline` - Get a baseline resume
- `GET /v1/resume/baseline/list` - Get a list of all baseline resumes
- `POST /v1/resume/clone` - Create a copy of a resume
- `GET /v1/resume/detail` - Get a resume detail record
- `POST /v1/resume/detail` - Create or update a resume_detail record
- `POST /v1/resume/extract` - Extract job title and keywords from resume
- `GET /v1/resume/job` - Get a list of resume with job info
- `GET /v1/resume/list` - Get a list of resumes
- `POST /v1/resume/rewrite` - Trigger rewrite of resume

### Personal
- `POST /v1/personal` - Create or update personal info
- `GET /v1/personal` - Get the personal info

## Project Structure

```
backend/
├── app/
│   ├── api/           # API route handlers
│   ├── core/          # Core configuration
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── utils/         # Utility functions
│   └── main.py        # FastAPI application
├── requirements.txt   # Dependencies
├── run.py            # Application runner
└── README.md         # This file
```

## Database Schema

The application uses the PostgreSQL schema defined in `docs/schema.sql` with tables for:
- Jobs and job tracking
- Contacts and relationships
- Calendar appointments
- Notes and documentation
- Resume and cover letter tracking
- Communication history

It uses foreign key enforcement for data integrity to require records between tables are associated correctly 
and that no orphaned data is possible.

## Development

### Code Organization

- **Models**: SQLAlchemy ORM models in `app/models/`
- **Schemas**: Pydantic models for request/response validation `app/schemas`
- **API Routes**: Organized by feature in `app/api/`
- **Database**: Connection and session management in `app/core/`
- **Utilities**: Helper functions for directory management and date handling `app/utils`
- **Prompts**: The prompts used for the AI requests for actions `app/utils/prompts`
- **Middleware**: Functionality injected into each route `app/middleware`

### Best Practices

- Soft deletes for data integrity
- Proper HTTP status codes
- Input validation with Pydantic
- Structured error handling
- CORS configuration for frontend integration
- Environment-based configuration