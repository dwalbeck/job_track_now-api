import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os


class TestSettingsDefaults:
    """Test suite for Settings default values."""

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_default_app_name(self):
        """Test default application name."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.app_name == "Job Track Now API"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_default_app_version(self):
        """Test default application version."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.app_version == "1.0.0"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_default_debug_false(self):
        """Test default debug mode is False."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.debug == False

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_default_log_level(self):
        """Test default log level."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.log_level == "INFO"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_default_log_file(self):
        """Test default log file name."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.log_file == "app.log"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_default_allowed_origins(self):
        """Test default allowed origins."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.allowed_origins == "*"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_default_postgres_port(self):
        """Test default PostgreSQL port."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.postgres_port == 5432


class TestSettingsEnvironmentVariables:
    """Test suite for loading settings from environment variables."""

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://user:pass@db.example.com/mydb",
        "POSTGRES_HOST": "db.example.com",
        "POSTGRES_USER": "user",
        "POSTGRES_PASSWORD": "pass",
        "POSTGRES_DB": "mydb",
        "BASE_JOB_FILE_PATH": "/app/jobs",
        "RESUME_DIR": "/app/resumes",
        "COVER_LETTER_DIR": "/app/letters",
        "EXPORT_DIR": "/app/export",
        "OPENAI_API_KEY": "sk-test123",
        "OPENAI_PROJECT": "project-123"
    }, clear=True)
    def test_loads_database_url_from_env(self):
        """Test loading database URL from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.database_url == "postgresql://user:pass@db.example.com/mydb"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "testhost",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass",
        "POSTGRES_DB": "testdb",
        "POSTGRES_PORT": "5433",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_loads_postgres_config_from_env(self):
        """Test loading PostgreSQL config from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.postgres_host == "testhost"
        assert settings.postgres_user == "testuser"
        assert settings.postgres_password == "testpass"
        assert settings.postgres_db == "testdb"
        assert settings.postgres_port == 5433

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/custom/jobs",
        "RESUME_DIR": "/custom/resumes",
        "COVER_LETTER_DIR": "/custom/letters",
        "EXPORT_DIR": "/custom/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_loads_file_paths_from_env(self):
        """Test loading file paths from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.base_job_file_path == "/custom/jobs"
        assert settings.resume_dir == "/custom/resumes"
        assert settings.cover_letter_dir == "/custom/letters"
        assert settings.export_dir == "/custom/export"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE": "custom.log",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_loads_logging_config_from_env(self):
        """Test loading logging config from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.log_level == "DEBUG"
        assert settings.log_file == "custom.log"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "sk-real-key",
        "OPENAI_PROJECT": "proj-123",
        "AI_MODEL": "gpt-4",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_loads_ai_config_from_env(self):
        """Test loading AI config from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.openai_api_key == "test-key"
        assert settings.openai_project == "test-project"


class TestGetAllowedOrigins:
    """Test suite for get_allowed_origins method."""

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "ALLOWED_ORIGINS": "*",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_get_allowed_origins_wildcard(self):
        """Test get_allowed_origins with wildcard."""
        from app.core.config import Settings

        settings = Settings()
        origins = settings.get_allowed_origins()

        assert origins == ["*"]

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "ALLOWED_ORIGINS": '["http://localhost:3000", "http://localhost:8000"]',
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_get_allowed_origins_json_array(self):
        """Test get_allowed_origins with JSON array."""
        from app.core.config import Settings

        settings = Settings()
        origins = settings.get_allowed_origins()

        assert isinstance(origins, list)
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "http://localhost:8000" in origins

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "ALLOWED_ORIGINS": "http://example.com",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_get_allowed_origins_single_string(self):
        """Test get_allowed_origins with single string (not JSON)."""
        from app.core.config import Settings

        settings = Settings()
        origins = settings.get_allowed_origins()

        assert origins == ["http://example.com"]

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_get_allowed_origins_with_list_type(self):
        """Test get_allowed_origins when already a list."""
        from app.core.config import Settings

        settings = Settings()
        settings.allowed_origins = ["http://example1.com", "http://example2.com"]

        origins = settings.get_allowed_origins()

        assert origins == ["http://example1.com", "http://example2.com"]


class TestLoadLlmSettingsFromDb:
    """Test suite for load_llm_settings_from_db method."""

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_load_llm_settings_success(self):
        """Test loading LLM settings from database."""
        from app.core.config import Settings

        settings = Settings()

        # Mock database
        mock_db = Mock()
        mock_result = Mock()
        mock_result.job_extract_llm = "gpt-4"
        mock_result.rewrite_llm = "gpt-4-turbo"
        mock_result.cover_llm = "gpt-4"
        mock_result.resume_extract_llm = "gpt-4o-mini"
        mock_result.openai_api_key = "sk-from-db"
        mock_db.execute.return_value.first.return_value = mock_result

        settings.load_llm_settings_from_db(mock_db)

        assert settings.job_extract_llm == "gpt-4"
        assert settings.rewrite_llm == "gpt-4-turbo"
        assert settings.cover_llm == "gpt-4"
        assert settings.resume_extract_llm == "gpt-4o-mini"
        assert settings.openai_api_key == "sk-from-db"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_load_llm_settings_no_result(self):
        """Test loading LLM settings when no records exist."""
        from app.core.config import Settings

        settings = Settings()
        original_model = settings.job_extract_llm

        # Mock database with no results
        mock_db = Mock()
        mock_db.execute.return_value.first.return_value = None

        settings.load_llm_settings_from_db(mock_db)

        # Should keep default values
        assert settings.job_extract_llm == original_model

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_load_llm_settings_partial_data(self):
        """Test loading LLM settings with partial data."""
        from app.core.config import Settings

        settings = Settings()
        original_cover = settings.cover_llm

        # Mock database with partial data
        mock_db = Mock()
        mock_result = Mock()
        mock_result.job_extract_llm = "gpt-4"
        mock_result.rewrite_llm = None  # NULL in database
        mock_result.cover_llm = None
        mock_result.resume_extract_llm = "gpt-4o-mini"
        mock_result.openai_api_key = None
        mock_db.execute.return_value.first.return_value = mock_result

        settings.load_llm_settings_from_db(mock_db)

        # Only non-NULL values should be updated
        assert settings.job_extract_llm == "gpt-4"
        assert settings.resume_extract_llm == "gpt-4o-mini"
        # NULL values should keep defaults
        assert settings.cover_llm == original_cover

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_load_llm_settings_database_error(self):
        """Test loading LLM settings when database error occurs."""
        from app.core.config import Settings

        settings = Settings()
        original_model = settings.job_extract_llm

        # Mock database error
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("Database connection failed")

        # Should not raise exception, just keep defaults
        settings.load_llm_settings_from_db(mock_db)

        assert settings.job_extract_llm == original_model


class TestSettingsModelConfig:
    """Test suite for Settings model configuration."""

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project",
        "EXTRA_FIELD": "should_be_ignored"
    }, clear=True)
    def test_extra_fields_ignored(self):
        """Test that extra fields from .env are ignored."""
        from app.core.config import Settings

        # Should not raise error for extra fields
        settings = Settings()

        assert settings is not None

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "BASE_JOB_FILE_PATH": "/tmp/jobs",
        "RESUME_DIR": "/tmp/resumes",
        "COVER_LETTER_DIR": "/tmp/letters",
        "EXPORT_DIR": "/tmp/export",
        "debug": "true",  # lowercase
        "OPENAI_API_KEY": "test-key",
        "OPENAI_PROJECT": "test-project"
    }, clear=True)
    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        from app.core.config import Settings

        settings = Settings()

        # Should accept lowercase 'debug' and convert to boolean
        assert settings.debug == True
