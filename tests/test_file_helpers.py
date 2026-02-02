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

            with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                mock_get_name.return_value = "John Doe"

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "resume", mock_db, user_id=1
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

            with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                mock_get_name.return_value = "Jane Smith"

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "cover_letter", mock_db, user_id=1
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

            with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                mock_get_name.return_value = "Test User"

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "cover_letter", mock_db, user_id=1
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

            with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                mock_get_name.return_value = "Alex Johnson"

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "custom_document", mock_db, user_id=1
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

            with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                mock_get_name.return_value = "Mary Jane Watson Parker"

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "resume", mock_db, user_id=1
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

            with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                mock_get_name.return_value = "JOHN DOE"

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "resume", mock_db, user_id=1
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

        with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
            mock_get_name.return_value = "John Doe"

            with pytest.raises(Exception):
                create_standardized_download_file(
                    "/nonexistent/file.pdf", "resume", mock_db, user_id=1
                )

    def test_create_standardized_download_file_empty_name(self):
        """Test creating file when user has no name."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Content")
            src_path = src.name

        try:
            mock_db = Mock()

            with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                mock_get_name.return_value = ""

                tmp_path, download_name, mime_type = create_standardized_download_file(
                    src_path, "resume", mock_db, user_id=1
                )

            # Should still work with empty name
            assert download_name == "resume-_.pdf"

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)

    def test_create_standardized_download_file_no_user_id(self):
        """Test that create_standardized_download_file raises error when user_id is not provided."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(b"Content")
            src_path = src.name

        try:
            mock_db = Mock()

            with pytest.raises(ValueError) as excinfo:
                create_standardized_download_file(
                    src_path, "resume", mock_db, user_id=None
                )

            assert "user_id is required" in str(excinfo.value)
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

                with patch('app.utils.file_helpers.get_personal_name') as mock_get_name:
                    mock_get_name.return_value = "Test User"

                    tmp_path, download_name, mime_type = create_standardized_download_file(
                        src_path, "resume", mock_db, user_id=1
                    )

                assert download_name.endswith(ext)
                assert os.path.exists(tmp_path)

                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            finally:
                if os.path.exists(src_path):
                    os.unlink(src_path)
