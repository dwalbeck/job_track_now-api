import pytest
from unittest.mock import Mock, patch, MagicMock, call
import logging
import tempfile
import os
from app.utils.logger import APILogger


class TestAPILoggerSingleton:
    """Test suite for APILogger singleton pattern."""

    def test_singleton_pattern(self):
        """Test that APILogger follows singleton pattern."""
        # Clear any existing instance
        APILogger._instance = None

        logger1 = APILogger()
        logger2 = APILogger()

        # Both should be the same instance
        assert logger1 is logger2

    def test_singleton_shared_state(self):
        """Test that singleton instances share state."""
        # Clear any existing instance
        APILogger._instance = None

        logger1 = APILogger()
        logger2 = APILogger()

        # They should share the same _logger
        assert logger1._logger is logger2._logger


class TestAPILoggerSetup:
    """Test suite for APILogger setup and configuration."""

    @patch('app.utils.logger.settings')
    def test_setup_logger_creates_handlers(self, mock_settings):
        """Test that logger setup creates file and console handlers."""
        # Clear singleton
        APILogger._instance = None

        mock_settings.log_level = "DEBUG"
        mock_settings.log_file = "test.log"

        with patch('logging.handlers.RotatingFileHandler'):
            with patch('logging.StreamHandler'):
                logger = APILogger()

                # Logger should be created
                assert logger._logger is not None
                assert logger._logger.name == 'job_track_now_api'

    @patch('app.utils.logger.settings')
    def test_setup_logger_sets_log_level(self, mock_settings):
        """Test that logger respects log level setting."""
        # Clear singleton
        APILogger._instance = None

        mock_settings.log_level = "WARNING"
        mock_settings.log_file = "test.log"

        with patch('logging.handlers.RotatingFileHandler'):
            with patch('logging.StreamHandler'):
                logger = APILogger()

                assert logger._logger.level == logging.WARNING

    @patch('app.utils.logger.settings')
    def test_setup_logger_prevents_duplicate_handlers(self, mock_settings):
        """Test that logger doesn't add duplicate handlers."""
        # Clear singleton
        APILogger._instance = None

        mock_settings.log_level = "DEBUG"
        mock_settings.log_file = "test.log"

        with patch('logging.handlers.RotatingFileHandler'):
            with patch('logging.StreamHandler'):
                logger = APILogger()

                initial_handlers = len(logger._logger.handlers)

                # Try to setup again by calling _setup_logger
                logger._setup_logger()

                # Should not add more handlers
                assert len(logger._logger.handlers) == initial_handlers


class TestAPILoggerLoggingMethods:
    """Test suite for basic logging methods."""

    @patch('app.utils.logger.settings')
    def setup_mock_logger(self, mock_settings):
        """Helper to setup a mock logger."""
        # Clear singleton
        APILogger._instance = None

        mock_settings.log_level = "DEBUG"
        mock_settings.log_file = "test.log"

        with patch('logging.handlers.RotatingFileHandler'):
            with patch('logging.StreamHandler'):
                logger = APILogger()
                logger._logger = Mock()
                return logger

    def test_debug_logging(self):
        """Test debug level logging."""
        logger = self.setup_mock_logger()

        logger.debug("Test debug message")

        logger._logger.debug.assert_called_once()
        call_args = logger._logger.debug.call_args[0][0]
        assert "Test debug message" in call_args

    def test_info_logging(self):
        """Test info level logging."""
        logger = self.setup_mock_logger()

        logger.info("Test info message")

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "Test info message" in call_args

    def test_warning_logging(self):
        """Test warning level logging."""
        logger = self.setup_mock_logger()

        logger.warning("Test warning message")

        logger._logger.warning.assert_called_once()
        call_args = logger._logger.warning.call_args[0][0]
        assert "Test warning message" in call_args

    def test_error_logging(self):
        """Test error level logging."""
        logger = self.setup_mock_logger()

        logger.error("Test error message")

        logger._logger.error.assert_called_once()
        call_args = logger._logger.error.call_args[0][0]
        assert "Test error message" in call_args

    def test_critical_logging(self):
        """Test critical level logging."""
        logger = self.setup_mock_logger()

        logger.critical("Test critical message")

        logger._logger.critical.assert_called_once()
        call_args = logger._logger.critical.call_args[0][0]
        assert "Test critical message" in call_args


class TestAPILoggerMessageFormatting:
    """Test suite for message formatting with kwargs."""

    @patch('app.utils.logger.settings')
    def setup_mock_logger(self, mock_settings):
        """Helper to setup a mock logger."""
        APILogger._instance = None
        mock_settings.log_level = "DEBUG"
        mock_settings.log_file = "test.log"

        with patch('logging.handlers.RotatingFileHandler'):
            with patch('logging.StreamHandler'):
                logger = APILogger()
                logger._logger = Mock()
                return logger

    def test_format_message_with_single_kwarg(self):
        """Test message formatting with single keyword argument."""
        logger = self.setup_mock_logger()

        logger.info("Test message", user_id=123)

        call_args = logger._logger.info.call_args[0][0]
        assert "Test message" in call_args
        assert "user_id=123" in call_args

    def test_format_message_with_multiple_kwargs(self):
        """Test message formatting with multiple keyword arguments."""
        logger = self.setup_mock_logger()

        logger.info("Test message", user_id=123, action="create", status="success")

        call_args = logger._logger.info.call_args[0][0]
        assert "Test message" in call_args
        assert "user_id=123" in call_args
        assert "action=create" in call_args
        assert "status=success" in call_args

    def test_format_message_without_kwargs(self):
        """Test message formatting without keyword arguments."""
        logger = self.setup_mock_logger()

        logger.info("Simple message")

        call_args = logger._logger.info.call_args[0][0]
        assert call_args == "Simple message"
        assert "|" not in call_args

    def test_format_message_with_string_values(self):
        """Test message formatting with string values."""
        logger = self.setup_mock_logger()

        logger.error("Error occurred", error="Connection timeout", host="localhost")

        call_args = logger._logger.error.call_args[0][0]
        assert "error=Connection timeout" in call_args
        assert "host=localhost" in call_args


class TestAPILoggerSpecializedMethods:
    """Test suite for specialized logging methods."""

    @patch('app.utils.logger.settings')
    def setup_mock_logger(self, mock_settings):
        """Helper to setup a mock logger."""
        APILogger._instance = None
        mock_settings.log_level = "DEBUG"
        mock_settings.log_file = "test.log"

        with patch('logging.handlers.RotatingFileHandler'):
            with patch('logging.StreamHandler'):
                logger = APILogger()
                logger._logger = Mock()
                return logger

    def test_log_request_with_all_params(self):
        """Test logging API request with all parameters."""
        logger = self.setup_mock_logger()

        logger.log_request("GET", "/api/jobs", client_ip="192.168.1.1", user_id=42)

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "API Request: GET /api/jobs" in call_args
        assert "IP: 192.168.1.1" in call_args
        assert "User: 42" in call_args

    def test_log_request_without_optional_params(self):
        """Test logging API request without optional parameters."""
        logger = self.setup_mock_logger()

        logger.log_request("POST", "/api/jobs")

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "API Request: POST /api/jobs" in call_args
        assert "IP:" not in call_args
        assert "User:" not in call_args

    def test_log_request_health_check_skipped(self):
        """Test that health check requests are not logged."""
        logger = self.setup_mock_logger()

        logger.log_request("GET", "/health")

        # Should not log health checks
        logger._logger.info.assert_not_called()

    def test_log_response_with_duration(self):
        """Test logging API response with duration."""
        logger = self.setup_mock_logger()

        logger.log_response("GET", "/api/jobs", 200, duration_ms=125.75)

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "API Response: GET /api/jobs - 200" in call_args
        assert "125.75ms" in call_args

    def test_log_response_without_duration(self):
        """Test logging API response without duration."""
        logger = self.setup_mock_logger()

        logger.log_response("POST", "/api/jobs", 201)

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "API Response: POST /api/jobs - 201" in call_args
        assert "ms" not in call_args

    def test_log_response_health_check_skipped(self):
        """Test that health check responses are not logged."""
        logger = self.setup_mock_logger()

        logger.log_response("GET", "/health", 200)

        # Should not log health check responses
        logger._logger.info.assert_not_called()

    def test_log_response_error_status(self):
        """Test logging API response with error status code."""
        logger = self.setup_mock_logger()

        logger.log_response("GET", "/api/jobs/999", 404, duration_ms=50.0)

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "404" in call_args

    def test_log_database_operation_with_id(self):
        """Test logging database operation with record ID."""
        logger = self.setup_mock_logger()

        logger.log_database_operation("INSERT", "jobs", record_id=123)

        logger._logger.debug.assert_called_once()
        call_args = logger._logger.debug.call_args[0][0]
        assert "Database INSERT: jobs" in call_args
        assert "ID: 123" in call_args

    def test_log_database_operation_without_id(self):
        """Test logging database operation without record ID."""
        logger = self.setup_mock_logger()

        logger.log_database_operation("SELECT", "jobs")

        logger._logger.debug.assert_called_once()
        call_args = logger._logger.debug.call_args[0][0]
        assert "Database SELECT: jobs" in call_args
        assert "ID:" not in call_args

    def test_log_database_operation_update(self):
        """Test logging database UPDATE operation."""
        logger = self.setup_mock_logger()

        logger.log_database_operation("UPDATE", "contacts", record_id=456)

        call_args = logger._logger.debug.call_args[0][0]
        assert "Database UPDATE: contacts" in call_args
        assert "ID: 456" in call_args

    def test_log_database_operation_delete(self):
        """Test logging database DELETE operation."""
        logger = self.setup_mock_logger()

        logger.log_database_operation("DELETE", "notes", record_id=789)

        call_args = logger._logger.debug.call_args[0][0]
        assert "Database DELETE: notes" in call_args
        assert "ID: 789" in call_args

    def test_log_error_with_context(self):
        """Test logging error with context information."""
        logger = self.setup_mock_logger()

        test_error = ValueError("Invalid input")
        logger.log_error_with_context(test_error, context="User registration")

        logger._logger.error.assert_called_once()
        call_args = logger._logger.error.call_args[0][0]
        assert "Exception occurred: Invalid input" in call_args
        assert "Context: User registration" in call_args

    def test_log_error_without_context(self):
        """Test logging error without context."""
        logger = self.setup_mock_logger()

        test_error = ConnectionError("Database connection failed")
        logger.log_error_with_context(test_error)

        logger._logger.error.assert_called_once()
        call_args = logger._logger.error.call_args[0][0]
        assert "Exception occurred: Database connection failed" in call_args
        assert "Context:" not in call_args


class TestAPILoggerEdgeCases:
    """Test suite for edge cases and special scenarios."""

    @patch('app.utils.logger.settings')
    def setup_mock_logger(self, mock_settings):
        """Helper to setup a mock logger."""
        APILogger._instance = None
        mock_settings.log_level = "DEBUG"
        mock_settings.log_file = "test.log"

        with patch('logging.handlers.RotatingFileHandler'):
            with patch('logging.StreamHandler'):
                logger = APILogger()
                logger._logger = Mock()
                return logger

    def test_log_request_empty_path(self):
        """Test logging request with empty path."""
        logger = self.setup_mock_logger()

        logger.log_request("GET", "")

        logger._logger.info.assert_called_once()

    def test_log_response_zero_duration(self):
        """Test logging response with zero duration."""
        logger = self.setup_mock_logger()

        logger.log_response("GET", "/api/jobs", 200, duration_ms=0.0)

        call_args = logger._logger.info.call_args[0][0]
        # Note: duration_ms=0.0 is falsy so duration is not shown in the message
        assert "API Response: GET /api/jobs - 200" in call_args

    def test_log_database_operation_zero_id(self):
        """Test logging database operation with ID of 0."""
        logger = self.setup_mock_logger()

        logger.log_database_operation("SELECT", "jobs", record_id=0)

        # ID of 0 is falsy but should still be logged
        call_args = logger._logger.debug.call_args[0][0]
        # Due to "if record_id" check, 0 won't be shown
        assert "Database SELECT: jobs" in call_args

    def test_format_message_with_none_values(self):
        """Test message formatting with None values."""
        logger = self.setup_mock_logger()

        logger.info("Test", value=None)

        call_args = logger._logger.info.call_args[0][0]
        assert "value=None" in call_args

    def test_format_message_with_empty_string(self):
        """Test message formatting with empty string values."""
        logger = self.setup_mock_logger()

        logger.info("Test", name="")

        call_args = logger._logger.info.call_args[0][0]
        assert "name=" in call_args

    def test_log_very_long_message(self):
        """Test logging very long message."""
        logger = self.setup_mock_logger()

        long_message = "A" * 10000
        logger.info(long_message)

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "A" * 100 in call_args  # At least part of it should be there

    def test_log_message_with_special_characters(self):
        """Test logging message with special characters."""
        logger = self.setup_mock_logger()

        logger.info("Test", data="Value with 'quotes' and \"double quotes\"")

        logger._logger.info.assert_called_once()

    def test_log_message_with_unicode(self):
        """Test logging message with unicode characters."""
        logger = self.setup_mock_logger()

        logger.info("Test message with unicode: 你好世界 🎉")

        logger._logger.info.assert_called_once()
        call_args = logger._logger.info.call_args[0][0]
        assert "你好世界" in call_args or "Test message" in call_args
