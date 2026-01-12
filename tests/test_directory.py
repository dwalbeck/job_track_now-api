import pytest
from unittest.mock import patch, Mock
from pathlib import Path
import tempfile
import os
from app.utils.directory import create_job_directory


class TestCreateJobDirectory:
    """Test suite for create_job_directory function."""

    @patch('app.utils.directory.settings')
    def test_create_job_directory_basic(self, mock_settings):
        """Test creating a job directory with basic input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Tech Corp", "Software Engineer")

            expected_path = os.path.join(tmpdir, "Tech_Corp", "Software_Engineer")
            assert result == expected_path
            assert os.path.exists(expected_path)
            assert os.path.isdir(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_with_spaces(self, mock_settings):
        """Test creating directory with spaces in company and title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Acme Software Solutions", "Senior Software Engineer")

            expected_path = os.path.join(tmpdir, "Acme_Software_Solutions", "Senior_Software_Engineer")
            assert result == expected_path
            assert os.path.exists(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_with_special_chars(self, mock_settings):
        """Test creating directory with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Tech@Corp!", "Software/Engineer")

            # Special chars should be removed
            expected_path = os.path.join(tmpdir, "TechCorp", "SoftwareEngineer")
            assert result == expected_path
            assert os.path.exists(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_with_hyphens(self, mock_settings):
        """Test creating directory with hyphens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Tech-Corp", "Software-Engineer")

            # Hyphens should be converted to underscores
            expected_path = os.path.join(tmpdir, "Tech_Corp", "Software_Engineer")
            assert result == expected_path
            assert os.path.exists(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_multiple_spaces(self, mock_settings):
        """Test creating directory with multiple consecutive spaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Tech   Corp", "Software    Engineer")

            # Multiple spaces should be converted to single underscore
            expected_path = os.path.join(tmpdir, "Tech_Corp", "Software_Engineer")
            assert result == expected_path
            assert os.path.exists(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_leading_trailing_spaces(self, mock_settings):
        """Test creating directory with leading/trailing spaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("  Tech Corp  ", "  Software Engineer  ")

            expected_path = os.path.join(tmpdir, "Tech_Corp", "Software_Engineer")
            assert result == expected_path
            assert os.path.exists(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_already_exists(self, mock_settings):
        """Test creating directory when it already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            # Create directory first time
            result1 = create_job_directory("Tech Corp", "Software Engineer")

            # Create same directory again (should not fail)
            result2 = create_job_directory("Tech Corp", "Software Engineer")

            assert result1 == result2
            assert os.path.exists(result2)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_nested_creation(self, mock_settings):
        """Test creating nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Tech Corp", "Software Engineer")

            # Both parent and child directories should exist
            parent_dir = os.path.join(tmpdir, "Tech_Corp")
            assert os.path.exists(parent_dir)
            assert os.path.exists(result)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_empty_strings(self, mock_settings):
        """Test creating directory with empty strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("", "")

            # Should still create directories (will be empty names)
            assert isinstance(result, str)
            assert tmpdir in result

    @patch('app.utils.directory.settings')
    def test_create_job_directory_unicode_chars(self, mock_settings):
        """Test creating directory with unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("TechCorp™", "Engineer©")

            # Special unicode chars should be removed
            assert "Tech" in result or "TechCorp" in result
            assert "Engineer" in result

    @patch('app.utils.directory.settings')
    def test_create_job_directory_numbers(self, mock_settings):
        """Test creating directory with numbers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Tech123 Corp", "Engineer L2")

            # Numbers should be preserved
            expected_path = os.path.join(tmpdir, "Tech123_Corp", "Engineer_L2")
            assert result == expected_path
            assert os.path.exists(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_permission_error(self, mock_settings):
        """Test creating directory when permission error occurs."""
        mock_settings.base_job_file_path = "/root/restricted"

        # Should return path even if creation fails
        result = create_job_directory("Tech Corp", "Engineer")

        # Result should contain the expected path structure
        assert "Tech_Corp" in result
        assert "Engineer" in result

    @patch('app.utils.directory.settings')
    @patch('pathlib.Path.mkdir')
    def test_create_job_directory_exception_handling(self, mock_mkdir, mock_settings):
        """Test that function handles mkdir exceptions gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir
            mock_mkdir.side_effect = OSError("Permission denied")

            # Should return path even when mkdir fails
            result = create_job_directory("Tech Corp", "Engineer")

            assert isinstance(result, str)
            assert "Tech_Corp" in result
            assert "Engineer" in result

    @patch('app.utils.directory.settings')
    def test_create_job_directory_mixed_case(self, mock_settings):
        """Test creating directory preserves case."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("TechCorp", "SoftwareEngineer")

            # Case should be preserved
            expected_path = os.path.join(tmpdir, "TechCorp", "SoftwareEngineer")
            assert result == expected_path
            assert os.path.exists(expected_path)

    @patch('app.utils.directory.settings')
    def test_create_job_directory_dots_and_underscores(self, mock_settings):
        """Test creating directory with dots and underscores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.base_job_file_path = tmpdir

            result = create_job_directory("Tech.Corp_Inc", "Software.Engineer_Senior")

            # Dots should be removed, underscores preserved
            assert os.path.exists(result)
            # Note: regex removes dots but preserves underscores initially,
            # then spaces are converted to underscores
