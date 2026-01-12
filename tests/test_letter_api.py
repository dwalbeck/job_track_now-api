import pytest
from unittest.mock import patch, MagicMock, mock_open
from sqlalchemy import text


class TestGetLetter:
    """Test suite for GET /v1/letter endpoint."""

    def test_get_letter_success(self, client, test_db):
        """Test getting a cover letter by ID."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Tech Corp', 'Engineer', 'applied', true, 'tech_corp_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Main Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, instruction, letter_content, file_name)
            VALUES (1, 1, 1, 'medium', 'professional', 'Focus on technical skills', '<p>Dear Hiring Manager,</p>', 'cover.docx')
        """))
        test_db.commit()

        response = client.get("/v1/letter?cover_id=1")

        assert response.status_code == 200
        data = response.json()
        assert data['cover_id'] == 1
        assert data['resume_id'] == 1
        assert data['job_id'] == 1
        assert data['letter_length'] == 'medium'
        assert data['letter_tone'] == 'professional'
        assert data['instruction'] == 'Focus on technical skills'
        assert data['file_name'] == 'cover.docx'

    def test_get_letter_not_found(self, client, test_db):
        """Test getting non-existent cover letter."""
        response = client.get("/v1/letter?cover_id=999")

        assert response.status_code == 404
        assert "not found" in response.json()['detail']

    def test_get_letter_with_null_filename(self, client, test_db):
        """Test getting a cover letter with NULL file_name."""
        # Create test data with NULL file_name
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Test Co', 'Developer', 'applied', true, 'test_co_developer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_content, file_name)
            VALUES (1, 1, 1, 'short', 'casual', '<p>Letter content</p>', NULL)
        """))
        test_db.commit()

        response = client.get("/v1/letter?cover_id=1")

        assert response.status_code == 200
        data = response.json()
        assert data['file_name'] == ""  # NULL should be converted to empty string


class TestGetLetterList:
    """Test suite for GET /v1/letter/list endpoint."""

    def test_get_letter_list_empty(self, client, test_db):
        """Test getting letter list when none exist."""
        response = client.get("/v1/letter/list")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_letter_list_multiple(self, client, test_db):
        """Test getting multiple cover letters."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES
                (1, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, 'Company B', 'Developer', 'applied', true, 'company_b_developer')
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_active)
            VALUES
                (1, 1, 1, 'medium', 'professional', true),
                (2, 1, 2, 'long', 'enthusiastic', true)
        """))
        test_db.commit()

        response = client.get("/v1/letter/list")

        assert response.status_code == 200
        letters = response.json()

        assert len(letters) == 2
        # Should be ordered by letter_created DESC
        assert all('company' in letter for letter in letters)
        assert all('job_title' in letter for letter in letters)

    def test_get_letter_list_excludes_inactive(self, client, test_db):
        """Test that inactive letters are excluded from list."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_active)
            VALUES
                (1, 1, 1, 'medium', 'professional', true),
                (2, 1, 1, 'short', 'casual', false)
        """))
        test_db.commit()

        response = client.get("/v1/letter/list")

        assert response.status_code == 200
        letters = response.json()

        assert len(letters) == 1
        assert letters[0]['cover_id'] == 1


class TestSaveLetter:
    """Test suite for POST /v1/letter endpoint."""

    @patch('app.api.letter.update_job_activity')
    def test_create_letter_success(self, mock_update_activity, client, test_db):
        """Test creating a new cover letter."""
        # Create test job and resume
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.commit()

        letter_data = {
            "resume_id": 1,
            "job_id": 1,
            "letter_length": "medium",
            "letter_tone": "professional",
            "instruction": "Highlight technical expertise",
            "letter_content": "<p>Sample letter content</p>",
            "file_name": "cover.docx"
        }

        response = client.post("/v1/letter", json=letter_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'cover_id' in data

        # Verify letter was created
        letter = test_db.execute(text(f"SELECT * FROM cover_letter WHERE cover_id = {data['cover_id']}")).first()
        assert letter.letter_length == 'medium'
        assert letter.letter_tone == 'professional'

        # Verify job was updated with cover_id
        job = test_db.execute(text("SELECT cover_id FROM job WHERE job_id = 1")).first()
        assert job.cover_id == data['cover_id']

        mock_update_activity.assert_called_once_with(test_db, 1)

    @patch('app.api.letter.update_job_activity')
    def test_update_letter_success(self, mock_update_activity, client, test_db):
        """Test updating an existing cover letter."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_content)
            VALUES (1, 1, 1, 'short', 'casual', '<p>Old content</p>')
        """))
        test_db.commit()

        update_data = {
            "cover_id": 1,
            "resume_id": 1,
            "job_id": 1,
            "letter_length": "long",
            "letter_tone": "enthusiastic",
            "instruction": "Updated instructions",
            "letter_content": "<p>Updated content</p>",
            "file_name": "updated.docx"
        }

        response = client.post("/v1/letter", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify letter was updated
        letter = test_db.execute(text("SELECT * FROM cover_letter WHERE cover_id = 1")).first()
        assert letter.letter_length == 'long'
        assert letter.letter_tone == 'enthusiastic'
        assert letter.instruction == 'Updated instructions'

    def test_create_letter_invalid_length(self, client, test_db):
        """Test creating letter with invalid letter_length."""
        letter_data = {
            "resume_id": 1,
            "job_id": 1,
            "letter_length": "invalid_length",
            "letter_tone": "professional"
        }

        response = client.post("/v1/letter", json=letter_data)

        assert response.status_code == 400
        assert "letter_length must be one of" in response.json()['detail']

    def test_create_letter_invalid_tone(self, client, test_db):
        """Test creating letter with invalid letter_tone."""
        letter_data = {
            "resume_id": 1,
            "job_id": 1,
            "letter_length": "medium",
            "letter_tone": "invalid_tone"
        }

        response = client.post("/v1/letter", json=letter_data)

        assert response.status_code == 400
        assert "letter_tone must be one of" in response.json()['detail']


class TestDeleteLetter:
    """Test suite for DELETE /v1/letter endpoint."""

    def test_delete_letter_success(self, client, test_db):
        """Test successfully deleting a cover letter."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_active)
            VALUES (1, 1, 1, 'medium', 'professional', true)
        """))
        test_db.commit()

        response = client.delete("/v1/letter?cover_id=1")

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify soft delete
        letter = test_db.execute(text("SELECT letter_active FROM cover_letter WHERE cover_id = 1")).first()
        assert letter.letter_active == False

    def test_delete_letter_not_found(self, client, test_db):
        """Test deleting non-existent cover letter."""
        response = client.delete("/v1/letter?cover_id=999")

        assert response.status_code == 404
        assert "not found" in response.json()['detail']


class TestWriteCoverLetter:
    """Test suite for POST /v1/letter/write endpoint."""

    @patch('app.api.letter.AiAgent')
    def test_write_cover_letter_success(self, mock_ai_agent_class, client, test_db):
        """Test generating cover letter with AI."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Tech Corp', 'Senior Engineer', 'applied', true, 'tech_corp_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc)
            VALUES (1, 'Build amazing software')
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_md_rewrite)
            VALUES (1, '# Resume Content')
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, instruction)
            VALUES (1, 1, 1, 'medium', 'professional', 'Focus on leadership')
        """))
        test_db.commit()

        # Mock AI agent
        mock_ai_instance = MagicMock()
        mock_ai_instance.write_cover_letter.return_value = {
            'letter_content': '<p>Generated cover letter content</p>'
        }
        mock_ai_agent_class.return_value = mock_ai_instance

        response = client.post("/v1/letter/write", json={"cover_id": 1})

        assert response.status_code == 200
        data = response.json()
        assert 'letter_content' in data
        assert data['letter_content'] == '<p>Generated cover letter content</p>'

        # Verify AI agent was called with correct parameters
        mock_ai_instance.write_cover_letter.assert_called_once()
        call_kwargs = mock_ai_instance.write_cover_letter.call_args[1]
        assert call_kwargs['letter_tone'] == 'professional'
        assert call_kwargs['letter_length'] == 'medium'
        assert call_kwargs['company'] == 'Tech Corp'
        assert call_kwargs['job_title'] == 'Senior Engineer'

        # Verify database was updated
        letter = test_db.execute(text("SELECT letter_content FROM cover_letter WHERE cover_id = 1")).first()
        assert letter.letter_content == '<p>Generated cover letter content</p>'

    def test_write_cover_letter_missing_cover_id(self, client, test_db):
        """Test write endpoint without cover_id."""
        response = client.post("/v1/letter/write", json={})

        assert response.status_code == 400
        assert "cover_id is required" in response.json()['detail']

    def test_write_cover_letter_not_found(self, client, test_db):
        """Test write with non-existent cover_id."""
        response = client.post("/v1/letter/write", json={"cover_id": 999})

        assert response.status_code == 404
        assert "not found" in response.json()['detail']

    @patch('app.api.letter.AiAgent')
    def test_write_cover_letter_ai_error(self, mock_ai_agent_class, client, test_db):
        """Test handling AI generation errors."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc)
            VALUES (1, 'Job description')
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_md_rewrite)
            VALUES (1, '# Resume')
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone)
            VALUES (1, 1, 1, 'medium', 'professional')
        """))
        test_db.commit()

        # Mock AI agent to return empty result
        mock_ai_instance = MagicMock()
        mock_ai_instance.write_cover_letter.return_value = {}
        mock_ai_agent_class.return_value = mock_ai_instance

        response = client.post("/v1/letter/write", json={"cover_id": 1})

        assert response.status_code == 500
        assert "AI processing error" in response.json()['detail']


class TestConvertCoverLetter:
    """Test suite for POST /v1/letter/convert endpoint."""

    @patch('app.api.letter.subprocess.run')
    @patch('app.api.letter.os.makedirs')
    @patch('app.api.letter.settings')
    def test_convert_cover_letter_success(self, mock_settings, mock_makedirs, mock_subprocess, client, test_db):
        """Test converting cover letter to DOCX."""
        mock_settings.cover_letter_dir = '/app/cover_letters'

        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Tech Corp', 'Software Engineer', 'applied', true, 'tech_corp_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_content)
            VALUES (1, 1, 1, 'medium', 'professional', '<p>Cover letter HTML content</p>')
        """))
        test_db.commit()

        # Mock successful pandoc conversion
        mock_subprocess.return_value = MagicMock(returncode=0)

        response = client.post("/v1/letter/convert", json={
            "cover_id": 1,
            "format": "docx"
        })

        assert response.status_code == 200
        data = response.json()
        assert 'file_name' in data
        assert data['file_name'] == 'tech_corp-software_engineer.docx'

        # Verify pandoc was called
        mock_subprocess.assert_called_once()

        # Verify database was updated
        letter = test_db.execute(text("SELECT file_name FROM cover_letter WHERE cover_id = 1")).first()
        assert letter.file_name == 'tech_corp-software_engineer.docx'

    def test_convert_cover_letter_missing_cover_id(self, client, test_db):
        """Test convert endpoint without cover_id."""
        response = client.post("/v1/letter/convert", json={"format": "docx"})

        assert response.status_code == 400
        assert "cover_id is required" in response.json()['detail']

    def test_convert_cover_letter_invalid_format(self, client, test_db):
        """Test convert with unsupported format."""
        response = client.post("/v1/letter/convert", json={
            "cover_id": 1,
            "format": "pdf"
        })

        assert response.status_code == 400
        assert "Only 'docx' format is currently supported" in response.json()['detail']

    def test_convert_cover_letter_not_found(self, client, test_db):
        """Test convert with non-existent cover_id."""
        response = client.post("/v1/letter/convert", json={
            "cover_id": 999,
            "format": "docx"
        })

        assert response.status_code == 404
        assert "not found" in response.json()['detail']

    def test_convert_cover_letter_empty_content(self, client, test_db):
        """Test convert with empty letter content."""
        # Create test data with NULL letter_content
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_content)
            VALUES (1, 1, 1, 'medium', 'professional', NULL)
        """))
        test_db.commit()

        response = client.post("/v1/letter/convert", json={
            "cover_id": 1,
            "format": "docx"
        })

        assert response.status_code == 400
        assert "Cover letter content is empty" in response.json()['detail']

    @patch('app.api.letter.subprocess.run')
    @patch('app.api.letter.os.makedirs')
    @patch('app.api.letter.settings')
    def test_convert_cover_letter_filename_sanitization(self, mock_settings, mock_makedirs, mock_subprocess, client, test_db):
        """Test that filename is properly sanitized."""
        mock_settings.cover_letter_dir = '/app/cover_letters'

        # Create test data with special characters in company/title
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory, average_score)
            VALUES (1, 'Company/Inc.', 'Software: Engineer*', 'applied', true, 'company_inc_engineer', 0.0)
        """))
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Resume', 'resume.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO cover_letter (cover_id, resume_id, job_id, letter_length, letter_tone, letter_content)
            VALUES (1, 1, 1, 'medium', 'professional', '<p>Content</p>')
        """))
        test_db.commit()

        mock_subprocess.return_value = MagicMock(returncode=0)

        response = client.post("/v1/letter/convert", json={
            "cover_id": 1,
            "format": "docx"
        })

        assert response.status_code == 200
        data = response.json()
        # Verify special characters are replaced with underscores and spaces are replaced
        assert '/' not in data['file_name']
        assert ':' not in data['file_name']
        assert '*' not in data['file_name']
        assert ' ' not in data['file_name']
        assert data['file_name'] == 'company_inc.-software__engineer_.docx'
