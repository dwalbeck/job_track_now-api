import logging
import logging.handlers
import os
from datetime import datetime
from ..core.config import settings


class APILogger:
    """Centralized logging utility for the Job Track Now API"""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APILogger, cls).__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self):
        """Configure the logger with file and console handlers"""
        self._logger = logging.getLogger('job_track_now_api')

        # Convert log level string to logging constant
        log_level = getattr(logging, settings.log_level.upper(), logging.DEBUG)
        self._logger.setLevel(log_level)

        # Prevent duplicate handlers
        if self._logger.handlers:
            return

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler - write to document root
        log_file_path = os.path.join(os.getcwd(), settings.log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)

        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)

        # Add handlers to logger
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._logger.debug(self._format_message(message, **kwargs))

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._logger.info(self._format_message(message, **kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._logger.warning(self._format_message(message, **kwargs))

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._logger.error(self._format_message(message, **kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._logger.critical(self._format_message(message, **kwargs))

    def log_request(self, method: str, path: str, client_ip: str = None, user_id: int = None):
        """Log API request"""
        extras = []
        if client_ip:
            extras.append(f"IP: {client_ip}")
        if user_id:
            extras.append(f"User: {user_id}")
        if path != '/health':
            extra_info = f" ({', '.join(extras)})" if extras else ""
            self.info(f"API Request: {method} {path}{extra_info}")

    def log_response(self, method: str, path: str, status_code: int, duration_ms: float = None):
        """Log API response"""
        if path != '/health':
            duration_info = f" ({duration_ms:.2f}ms)" if duration_ms else ""
            self.info(f"API Response: {method} {path} - {status_code}{duration_info}")

    def log_database_operation(self, operation: str, table: str, record_id: int = None):
        """Log database operations"""
        record_info = f" ID: {record_id}" if record_id else ""
        self.debug(f"Database {operation}: {table}{record_info}")

    def log_error_with_context(self, error: Exception, context: str = ""):
        """Log error with context information"""
        context_info = f" - Context: {context}" if context else ""
        self.error(f"Exception occurred: {str(error)}{context_info}", exc_info=True)

    def _format_message(self, message: str, **kwargs) -> str:
        """Format log message with additional context"""
        if kwargs:
            context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{message} | {context}"
        return message


# Create global logger instance
logger = APILogger()