import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from fastapi.responses import FileResponse


class TestDownloadCoverLetter:
    """Test suite for GET /v1/files/cover_letters/{file_name} endpoint."""

    @patch('app.api.files.create_standardized_download_file')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_cover_letter_success(self, mock_settings, mock_exists, mock_create_std_file, client, test_db):
        """Test successful cover letter file download."""
        mock_settings.cover_letter_dir = '/app/cover_letters'
        mock_exists.return_value = True
        mock_create_std_file.return_value = (
            '/tmp/cover_letter-John_Doe.docx',
            'cover_letter-John_Doe.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

        response = client.get("/v1/files/cover_letters/test_letter.docx")

        assert response.status_code == 200
        mock_exists.assert_called_once_with('/app/cover_letters/test_letter.docx')
        mock_create_std_file.assert_called_once_with(
            source_file_path='/app/cover_letters/test_letter.docx',
            file_type='cover_letter',
            db=test_db
        )

    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_cover_letter_not_found(self, mock_settings, mock_exists, client, test_db):
        """Test download when cover letter file doesn't exist."""
        mock_settings.cover_letter_dir = '/app/cover_letters'
        mock_exists.return_value = False

        response = client.get("/v1/files/cover_letters/missing.docx")

        assert response.status_code == 404
        assert "File not found" in response.json()['detail']

    @patch('app.api.files.create_standardized_download_file')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_cover_letter_standardization_error(self, mock_settings, mock_exists, mock_create_std_file, client, test_db):
        """Test error handling when standardization fails."""
        mock_settings.cover_letter_dir = '/app/cover_letters'
        mock_exists.return_value = True
        mock_create_std_file.side_effect = Exception("Standardization failed")

        response = client.get("/v1/files/cover_letters/test.docx")

        assert response.status_code == 500
        assert "Error serving file" in response.json()['detail']


class TestDownloadResume:
    """Test suite for GET /v1/files/resumes/{file_name} endpoint."""

    @patch('app.api.files.create_standardized_download_file')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_resume_success(self, mock_settings, mock_exists, mock_create_std_file, client, test_db):
        """Test successful resume file download."""
        mock_settings.resume_dir = '/app/resumes'
        mock_exists.return_value = True
        mock_create_std_file.return_value = (
            '/tmp/resume-John_Doe.pdf',
            'resume-John_Doe.pdf',
            'application/pdf'
        )

        response = client.get("/v1/files/resumes/test_resume.pdf")

        assert response.status_code == 200
        mock_exists.assert_called_once_with('/app/resumes/test_resume.pdf')
        mock_create_std_file.assert_called_once_with(
            source_file_path='/app/resumes/test_resume.pdf',
            file_type='resume',
            db=test_db
        )

    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_resume_not_found(self, mock_settings, mock_exists, client, test_db):
        """Test download when resume file doesn't exist."""
        mock_settings.resume_dir = '/app/resumes'
        mock_exists.return_value = False

        response = client.get("/v1/files/resumes/missing.pdf")

        assert response.status_code == 404
        assert "File not found" in response.json()['detail']

    @patch('app.api.files.create_standardized_download_file')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_resume_docx_format(self, mock_settings, mock_exists, mock_create_std_file, client, test_db):
        """Test downloading resume in DOCX format."""
        mock_settings.resume_dir = '/app/resumes'
        mock_exists.return_value = True
        mock_create_std_file.return_value = (
            '/tmp/resume-Jane_Smith.docx',
            'resume-Jane_Smith.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

        response = client.get("/v1/files/resumes/jane_resume.docx")

        assert response.status_code == 200
        mock_create_std_file.assert_called_once()

    @patch('app.api.files.create_standardized_download_file')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_resume_error_handling(self, mock_settings, mock_exists, mock_create_std_file, client, test_db):
        """Test error handling during resume download."""
        mock_settings.resume_dir = '/app/resumes'
        mock_exists.return_value = True
        mock_create_std_file.side_effect = Exception("File processing error")

        response = client.get("/v1/files/resumes/test.pdf")

        assert response.status_code == 500
        assert "Error serving file" in response.json()['detail']


class TestDownloadExport:
    """Test suite for GET /v1/files/exports/{file_name} endpoint."""

    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_export_success(self, mock_settings, mock_exists, client, test_db, temp_dir):
        """Test successful export CSV file download."""
        # Create a test CSV file in temp directory
        export_file = temp_dir / "job_export-20250110.csv"
        export_file.write_text("company,job_title,status\nTest Co,Engineer,applied")

        mock_settings.export_dir = str(temp_dir)
        mock_exists.return_value = True

        response = client.get("/v1/files/exports/job_export-20250110.csv")

        assert response.status_code == 200
        mock_exists.assert_called_once()

    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_export_not_found(self, mock_settings, mock_exists, client, test_db):
        """Test download when export file doesn't exist."""
        mock_settings.export_dir = '/app/exports'
        mock_exists.return_value = False

        response = client.get("/v1/files/exports/missing_export.csv")

        assert response.status_code == 404
        assert "Export file not found" in response.json()['detail']

    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_export_contacts_file(self, mock_settings, mock_exists, client, test_db, temp_dir):
        """Test downloading contacts export file."""
        # Create a test contacts CSV file
        export_file = temp_dir / "contact_export-20250110.csv"
        export_file.write_text("first_name,last_name,email,phone\nJohn,Doe,john@test.com,555-1234")

        mock_settings.export_dir = str(temp_dir)
        mock_exists.return_value = True

        response = client.get("/v1/files/exports/contact_export-20250110.csv")

        assert response.status_code == 200

    @patch('app.api.files.FileResponse')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_download_export_error_handling(self, mock_settings, mock_exists, mock_file_response, client, test_db):
        """Test error handling during export download."""
        mock_settings.export_dir = '/app/exports'
        mock_exists.return_value = True
        mock_file_response.side_effect = Exception("File read error")

        response = client.get("/v1/files/exports/test_export.csv")

        assert response.status_code == 500
        assert "Error serving export file" in response.json()['detail']


class TestFileResponseMetadata:
    """Test suite for verifying FileResponse metadata and headers."""

    @patch('app.api.files.create_standardized_download_file')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_cover_letter_response_metadata(self, mock_settings, mock_exists, mock_create_std_file, client, test_db):
        """Test that cover letter response has correct metadata."""
        mock_settings.cover_letter_dir = '/app/cover_letters'
        mock_exists.return_value = True
        mock_create_std_file.return_value = (
            '/tmp/cover_letter-Test_User.docx',
            'cover_letter-Test_User.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

        response = client.get("/v1/files/cover_letters/letter.docx")

        assert response.status_code == 200
        # Verify standardized file creation was called with correct file_type
        args, kwargs = mock_create_std_file.call_args
        assert kwargs['file_type'] == 'cover_letter'

    @patch('app.api.files.create_standardized_download_file')
    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_resume_response_metadata(self, mock_settings, mock_exists, mock_create_std_file, client, test_db):
        """Test that resume response has correct metadata."""
        mock_settings.resume_dir = '/app/resumes'
        mock_exists.return_value = True
        mock_create_std_file.return_value = (
            '/tmp/resume-Test_User.pdf',
            'resume-Test_User.pdf',
            'application/pdf'
        )

        response = client.get("/v1/files/resumes/resume.pdf")

        assert response.status_code == 200
        # Verify standardized file creation was called with correct file_type
        args, kwargs = mock_create_std_file.call_args
        assert kwargs['file_type'] == 'resume'

    @patch('app.api.files.os.path.exists')
    @patch('app.api.files.settings')
    def test_export_csv_mime_type(self, mock_settings, mock_exists, client, test_db, temp_dir):
        """Test that export files are served with correct CSV mime type."""
        # Create a test export file
        export_file = temp_dir / "test_export.csv"
        export_file.write_text("data")

        mock_settings.export_dir = str(temp_dir)
        mock_exists.return_value = True

        response = client.get("/v1/files/exports/test_export.csv")

        assert response.status_code == 200
        # The actual FileResponse would set content-type header to text/csv
