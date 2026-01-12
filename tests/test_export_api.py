import pytest
import os
import csv
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from datetime import datetime


class TestExportJobs:
    """Test suite for GET /v1/export/job endpoint."""

    @patch('app.api.export.settings')
    def test_export_jobs_success(self, mock_settings, client, test_db, temp_dir):
        """Test successful job export."""
        mock_settings.export_dir = str(temp_dir)

        # Create test jobs
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, salary, location, interest_level, average_score)
            VALUES
                (100, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer', '100k-120k', 'SF, CA', 8, 0.0),
                (101, 'Company B', 'Developer', 'interviewing', true, 'company_b_developer', '90k-110k', 'NYC, NY', 9, 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc, job_qualification, job_keyword)
            VALUES
                (100, 'Build software', 'BS required', ARRAY['Python', 'React']),
                (101, 'Develop apps', 'MS preferred', ARRAY['Java', 'Spring'])
        """))
        test_db.commit()

        response = client.get("/v1/export/job")

        assert response.status_code == 200
        data = response.json()

        assert 'job_export_dir' in data
        assert 'job_export_file' in data
        assert data['job_export_dir'] == str(temp_dir)
        assert 'job_export-' in data['job_export_file']
        assert data['job_export_file'].endswith('.csv')

        # Verify file was created
        file_path = os.path.join(str(temp_dir), data['job_export_file'])
        assert os.path.exists(file_path)

        # Verify CSV content
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            assert len(rows) == 2
            # Order-agnostic check - verify both companies are present
            companies = {row['company'] for row in rows}
            assert companies == {'Company A', 'Company B'}

    def test_export_jobs_no_data(self, client, test_db):
        """Test export when no jobs exist."""
        # Ensure database is clean
        test_db.execute(text("DELETE FROM job_detail"))
        test_db.execute(text("DELETE FROM job"))
        test_db.commit()

        response = client.get("/v1/export/job")

        assert response.status_code == 404
        assert "No job data found to export" in response.json()['detail']

    @patch('app.api.export.settings')
    def test_export_jobs_handles_arrays(self, mock_settings, client, test_db, temp_dir):
        """Test that PostgreSQL arrays are properly converted in CSV."""
        mock_settings.export_dir = str(temp_dir)

        # Create test job with array data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (102, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc, job_keyword)
            VALUES (102, 'Description', ARRAY['Python', 'JavaScript', 'Docker'])
        """))
        test_db.commit()

        response = client.get("/v1/export/job")

        assert response.status_code == 200
        data = response.json()

        # Verify array was converted to comma-separated string
        file_path = os.path.join(str(temp_dir), data['job_export_file'])
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            assert 'Python, JavaScript, Docker' in rows[0]['job_keyword']


class TestExportContacts:
    """Test suite for GET /v1/export/contacts endpoint."""

    @patch('app.api.export.settings')
    def test_export_contacts_success(self, mock_settings, client, test_db, temp_dir):
        """Test successful contact export."""
        mock_settings.export_dir = str(temp_dir)

        # Create test contacts
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, email, phone, company, contact_active)
            VALUES
                (100, 'John', 'Doe', 'john@example.com', '555-1234', 'Company A', true),
                (101, 'Jane', 'Smith', 'jane@example.com', '555-5678', 'Company B', true)
        """))
        test_db.commit()

        response = client.get("/v1/export/contacts")

        assert response.status_code == 200
        data = response.json()

        assert 'contact_export_dir' in data
        assert 'contact_export_file' in data
        assert 'contact_export-' in data['contact_export_file']
        assert data['contact_export_file'].endswith('.csv')

        # Verify file was created
        file_path = os.path.join(str(temp_dir), data['contact_export_file'])
        assert os.path.exists(file_path)

        # Verify CSV content
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            assert len(rows) == 2
            first_names = {row['first_name'] for row in rows}
            assert first_names == {'John', 'Jane'}

    def test_export_contacts_no_data(self, client, test_db):
        """Test export when no contacts exist."""
        # Ensure database is clean
        test_db.execute(text("DELETE FROM contact"))
        test_db.commit()

        response = client.get("/v1/export/contacts")

        assert response.status_code == 404
        assert "No contact data found to export" in response.json()['detail']


class TestExportNotes:
    """Test suite for GET /v1/export/notes endpoint."""

    @patch('app.api.export.settings')
    def test_export_notes_success(self, mock_settings, client, test_db, temp_dir):
        """Test successful notes export."""
        mock_settings.export_dir = str(temp_dir)

        # Create test job and notes
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (103, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_content)
            VALUES
                (100, 103, 'Important note 1'),
                (101, 103, 'Important note 2')
        """))
        test_db.commit()

        response = client.get("/v1/export/notes")

        assert response.status_code == 200
        data = response.json()

        assert 'note_export_dir' in data
        assert 'note_export_file' in data
        assert 'note_export-' in data['note_export_file']

        # Verify file was created
        file_path = os.path.join(str(temp_dir), data['note_export_file'])
        assert os.path.exists(file_path)

    def test_export_notes_no_data(self, client, test_db):
        """Test export when no notes exist."""
        response = client.get("/v1/export/notes")

        assert response.status_code == 404
        assert "No note data found to export" in response.json()['detail']


class TestExportCalendar:
    """Test suite for GET /v1/export/calendar endpoint."""

    @patch('app.api.export.settings')
    def test_export_calendar_success(self, mock_settings, client, test_db, temp_dir):
        """Test successful calendar export."""
        mock_settings.export_dir = str(temp_dir)

        # Create test job and calendar events
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (104, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, job_id, calendar_type, start_date, start_time, participant)
            VALUES
                (100, 104, 'phone_call', '2025-01-15', '10:00:00', ARRAY['John Doe']),
                (101, 104, 'interview', '2025-01-20', '14:00:00', ARRAY['Jane Smith'])
        """))
        test_db.commit()

        response = client.get("/v1/export/calendar")

        assert response.status_code == 200
        data = response.json()

        assert 'calendar_export_dir' in data
        assert 'calendar_export_file' in data
        assert 'calendar_export-' in data['calendar_export_file']

        # Verify file was created
        file_path = os.path.join(str(temp_dir), data['calendar_export_file'])
        assert os.path.exists(file_path)

        # Verify CSV content includes array handling
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            assert len(rows) == 2

    def test_export_calendar_no_data(self, client, test_db):
        """Test export when no calendar events exist."""
        # Ensure database is clean
        test_db.execute(text("DELETE FROM calendar"))
        test_db.commit()

        response = client.get("/v1/export/calendar")

        assert response.status_code == 404
        assert "No calendar data found to export" in response.json()['detail']


class TestExportResumes:
    """Test suite for GET /v1/export/resumes endpoint."""

    @patch('app.api.export.settings')
    def test_export_resumes_success(self, mock_settings, client, test_db, temp_dir):
        """Test successful resumes export."""
        mock_settings.export_dir = str(temp_dir)

        # Create test resumes
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES
                (100, 'Main Resume', 'main.pdf', 'pdf', true, true, true),
                (101, 'Alt Resume', 'alt.docx', 'docx', true, false, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown, keyword_count, focus_count)
            VALUES
                (100, '# Resume 1', 25, 10),
                (101, '# Resume 2', 30, 12)
        """))
        test_db.commit()

        response = client.get("/v1/export/resumes")

        assert response.status_code == 200
        data = response.json()

        assert 'resume_export_dir' in data
        assert 'resume_export_file' in data
        assert 'resumes_export-' in data['resume_export_file']

        # Verify file was created
        file_path = os.path.join(str(temp_dir), data['resume_export_file'])
        assert os.path.exists(file_path)

        # Verify CSV content
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            assert len(rows) == 2
            resume_titles = {row['resume_title'] for row in rows}
            assert resume_titles == {'Main Resume', 'Alt Resume'}

    def test_export_resumes_no_data(self, client, test_db):
        """Test export when no resumes exist."""
        # Ensure database is clean
        test_db.execute(text("DELETE FROM resume_detail"))
        test_db.execute(text("DELETE FROM resume"))
        test_db.commit()

        response = client.get("/v1/export/resumes")

        assert response.status_code == 404
        assert "No resume data found to export" in response.json()['detail']

    @patch('app.api.export.settings')
    def test_export_resumes_handles_nulls(self, mock_settings, client, test_db, temp_dir):
        """Test that NULL values are properly handled in export."""
        mock_settings.export_dir = str(temp_dir)

        # Create resume with some NULL fields
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (102, 'Test Resume', NULL, 'pdf', true, true, true)
        """))
        test_db.commit()

        response = client.get("/v1/export/resumes")

        assert response.status_code == 200
        data = response.json()

        # Verify file was created and NULL values don't cause errors
        file_path = os.path.join(str(temp_dir), data['resume_export_file'])
        assert os.path.exists(file_path)

        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            # Should contain only the newly created resume
            assert len(rows) >= 1
            # Find the resume we just created
            test_resume = [r for r in rows if r['resume_id'] == '102']
            assert len(test_resume) == 1
