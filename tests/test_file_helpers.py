import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import text
import os
import tempfile
from pathlib import Path
from app.utils.file_helpers import (
    get_personal_name,
    get_file_extension,
    get_mime_type,
    create_standardized_download_file
)


class TestGetPersonalName:
    """Test suite for get_personal_name function."""

    def test_get_personal_name_success(self):
        """Test getting personal name successfully."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.first_name = "John"
        mock_result.last_name = "Doe"
        mock_db.execute.return_value.first.return_value = mock_result

        first_name, last_name = get_personal_name(mock_db)

        assert first_name == "John"
        assert last_name == "Doe"
        mock_db.execute.assert_called_once()

    def test_get_personal_name_no_result(self):
        """Test getting personal name when no records exist."""
        mock_db = Mock()
        mock_db.execute.return_value.first.return_value = None

        first_name, last_name = get_personal_name(mock_db)

        assert first_name == ""
        assert last_name == ""

    def test_get_personal_name_null_first_name(self):
        """Test getting personal name when first_name is NULL."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.first_name = None
        mock_result.last_name = "Doe"
        mock_db.execute.return_value.first.return_value = mock_result

        first_name, last_name = get_personal_name(mock_db)

        assert first_name == ""
        assert last_name == "Doe"

    def test_get_personal_name_null_last_name(self):
        """Test getting personal name when last_name is NULL."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.first_name = "John"
        mock_result.last_name = None
        mock_db.execute.return_value.first.return_value = mock_result

        first_name, last_name = get_personal_name(mock_db)

        assert first_name == "John"
        assert last_name == ""

    def test_get_personal_name_both_null(self):
        """Test getting personal name when both names are NULL."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.first_name = None
        mock_result.last_name = None
        mock_db.execute.return_value.first.return_value = mock_result

        first_name, last_name = get_personal_name(mock_db)

        assert first_name == ""
        assert last_name == ""

    def test_get_personal_name_database_error(self):
        """Test getting personal name when database error occurs."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("Database connection failed")

        first_name, last_name = get_personal_name(mock_db)

        # Should return empty strings on error
        assert first_name == ""
        assert last_name == ""

    def test_get_personal_name_with_spaces(self):
        """Test getting personal name with extra spaces."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.first_name = "  John  "
        mock_result.last_name = "  Doe  "
        mock_db.execute.return_value.first.return_value = mock_result

        first_name, last_name = get_personal_name(mock_db)

        # Function returns as-is, doesn't strip
        assert first_name == "  John  "
        assert last_name == "  Doe  "


class TestGetFileExtension:
    """Test suite for get_file_extension function."""

    def test_get_file_extension_pdf(self):
        """Test getting PDF file extension."""
        extension = get_file_extension("/path/to/file.pdf")
        assert extension == ".pdf"

    def test_get_file_extension_docx(self):
        """Test getting DOCX file extension."""
        extension = get_file_extension("/path/to/resume.docx")
        assert extension == ".docx"

    def test_get_file_extension_odt(self):
        """Test getting ODT file extension."""
        extension = get_file_extension("document.odt")
        assert extension == ".odt"

    def test_get_file_extension_no_extension(self):
        """Test getting extension from file without extension."""
        extension = get_file_extension("/path/to/file")
        assert extension == ""

    def test_get_file_extension_multiple_dots(self):
        """Test getting extension from file with multiple dots."""
        extension = get_file_extension("file.backup.pdf")
        assert extension == ".pdf"

    def test_get_file_extension_hidden_file(self):
        """Test getting extension from hidden file."""
        extension = get_file_extension(".gitignore")
        assert extension == ""

    def test_get_file_extension_hidden_with_extension(self):
        """Test getting extension from hidden file with extension."""
        extension = get_file_extension(".config.yaml")
        assert extension == ".yaml"

    def test_get_file_extension_uppercase(self):
        """Test getting extension with uppercase."""
        extension = get_file_extension("FILE.PDF")
        assert extension == ".PDF"


class TestGetMimeType:
    """Test suite for get_mime_type function."""

    def test_get_mime_type_pdf(self):
        """Test getting MIME type for PDF."""
        mime_type = get_mime_type("file.pdf")
        assert mime_type == "application/pdf"

    def test_get_mime_type_docx(self):
        """Test getting MIME type for DOCX."""
        mime_type = get_mime_type("file.docx")
        assert mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_get_mime_type_odt(self):
        """Test getting MIME type for ODT."""
        mime_type = get_mime_type("file.odt")
        assert mime_type == "application/vnd.oasis.opendocument.text"

    def test_get_mime_type_txt(self):
        """Test getting MIME type for text file."""
        mime_type = get_mime_type("file.txt")
        assert mime_type == "text/plain"

    def test_get_mime_type_html(self):
        """Test getting MIME type for HTML."""
        mime_type = get_mime_type("file.html")
        assert mime_type == "text/html"

    def test_get_mime_type_unknown(self):
        """Test getting MIME type for unknown extension."""
        mime_type = get_mime_type("file.xyz")
        assert mime_type == "application/octet-stream"

    def test_get_mime_type_no_extension(self):
        """Test getting MIME type for file without extension."""
        mime_type = get_mime_type("file")
        assert mime_type == "application/octet-stream"

    def test_get_mime_type_case_insensitive(self):
        """Test getting MIME type is case insensitive."""
        mime_type_lower = get_mime_type("file.pdf")
        mime_type_upper = get_mime_type("file.PDF")
        assert mime_type_lower == mime_type_upper


class TestCreateStandardizedDownloadFile:
    """Test suite for create_standardized_download_file function."""

    def test_create_standardized_download_file_resume(self):
        """Test creating standardized download file for resume."""
        # Create temporary source file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Resume content")
            src_path = src.name

        try:
            # Mock database
            mock_db = Mock()
            mock_result = Mock()
            mock_result.first_name = "John"
            mock_result.last_name = "Doe"
            mock_db.execute.return_value.first.return_value = mock_result

            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "resume", mock_db
            )

            assert download_name == "resume-john_doe.pdf"
            assert mime_type == "application/pdf"
            assert os.path.exists(tmp_path)
            assert tmp_path.startswith("/tmp/")

            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            # Clean up source file
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_cover_letter(self):
        """Test creating standardized download file for cover letter."""
        # Create temporary source file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as src:
            src.write(b"Cover letter content")
            src_path = src.name

        try:
            # Mock database
            mock_db = Mock()
            mock_result = Mock()
            mock_result.first_name = "Jane"
            mock_result.last_name = "Smith"
            mock_db.execute.return_value.first.return_value = mock_result

            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "cover_letter", mock_db
            )

            # Cover letters should always use .docx extension
            assert download_name == "cover_letter-jane_smith.docx"
            assert os.path.exists(tmp_path)

            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            # Clean up source file
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_cover_letter_forces_docx(self):
        """Test that cover letters always get .docx extension regardless of source."""
        # Create source file with .pdf extension
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Cover letter content")
            src_path = src.name

        try:
            # Mock database
            mock_db = Mock()
            mock_result = Mock()
            mock_result.first_name = "Test"
            mock_result.last_name = "User"
            mock_db.execute.return_value.first.return_value = mock_result

            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "cover_letter", mock_db
            )

            # Should use .docx even though source is .pdf
            assert download_name == "cover_letter-test_user.docx"

            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_custom_type(self):
        """Test creating standardized download file with custom type."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as src:
            src.write(b"Custom content")
            src_path = src.name

        try:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.first_name = "Alex"
            mock_result.last_name = "Johnson"
            mock_db.execute.return_value.first.return_value = mock_result

            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "custom_document", mock_db
            )

            assert download_name == "custom_document-alex_johnson.txt"
            assert mime_type == "text/plain"

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_spaces_in_name(self):
        """Test creating file with spaces in user name."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Content")
            src_path = src.name

        try:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.first_name = "Mary Jane"
            mock_result.last_name = "Watson Parker"
            mock_db.execute.return_value.first.return_value = mock_result

            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "resume", mock_db
            )

            # Spaces should be replaced with underscores
            assert download_name == "resume-mary_jane_watson_parker.pdf"

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_lowercase_name(self):
        """Test that download filename is lowercase."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Content")
            src_path = src.name

        try:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.first_name = "JOHN"
            mock_result.last_name = "DOE"
            mock_db.execute.return_value.first.return_value = mock_result

            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "resume", mock_db
            )

            # Name should be lowercase
            assert download_name == "resume-john_doe.pdf"

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_source_not_found(self):
        """Test creating file when source doesn't exist."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.first_name = "John"
        mock_result.last_name = "Doe"
        mock_db.execute.return_value.first.return_value = mock_result

        with pytest.raises(Exception):
            create_standardized_download_file(
                "/nonexistent/file.pdf", "resume", mock_db
            )

    def test_create_standardized_download_file_empty_name(self):
        """Test creating file when user has no name."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Content")
            src_path = src.name

        try:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.first_name = ""
            mock_result.last_name = ""
            mock_db.execute.return_value.first.return_value = mock_result

            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "resume", mock_db
            )

            # Should still work with empty name
            assert download_name == "resume-_.pdf"

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_db_error(self):
        """Test creating file when database error occurs."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Content")
            src_path = src.name

        try:
            mock_db = Mock()
            mock_db.execute.side_effect = Exception("Database error")

            # Should still work with empty name (from error handling)
            tmp_path, download_name, mime_type = create_standardized_download_file(
                src_path, "resume", mock_db
            )

            assert download_name == "resume-_.pdf"

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_different_extensions(self):
        """Test creating files with various extensions."""
        extensions = ['.pdf', '.docx', '.odt', '.txt', '.html']

        for ext in extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as src:
                src.write(b"Content")
                src_path = src.name

            try:
                mock_db = Mock()
                mock_result = Mock()
                mock_result.first_name = "Test"
                mock_result.last_name = "User"
                mock_db.execute.return_value.first.return_value = mock_result

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "resume", mock_db
                )

                assert download_name.endswith(ext)
                assert os.path.exists(tmp_path)

                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            finally:
                if os.path.exists(src_path):
                    os.unlink(src_path)
