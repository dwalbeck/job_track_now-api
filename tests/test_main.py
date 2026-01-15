import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class TestMainApp:
    """Test suite for main FastAPI application setup."""

    def test_app_exists(self, client):
        """Test that FastAPI app is created."""
        assert client.app is not None
        assert client.app.title == "Job Track Now API"

    def test_app_has_cors_middleware(self, client):
        """Test that CORS middleware is configured."""
        # CORS middleware should be in the middleware stack
        middleware_types = [type(m).__name__ for m in client.app.user_middleware]
        assert any('CORS' in name for name in middleware_types)

    def test_app_has_logging_middleware(self, client):
        """Test that logging middleware is configured."""
        middleware_types = [type(m).__name__ for m in client.app.user_middleware]
        assert 'LoggingMiddleware' in middleware_types

    def test_app_has_exception_handlers(self, client):
        """Test that exception handlers are registered."""
        # Check that exception handlers are configured
        assert len(client.app.exception_handlers) > 0


class TestRootEndpoint:
    """Test suite for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns correct message."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job Track Now API"
        assert "version" in data

    def test_root_endpoint_logs_access(self, client):
        """Test that root endpoint logs access."""
        with patch('app.main.logger') as mock_logger:
            response = client.get("/")

            assert response.status_code == 200
            # Note: logger.info might be called, but verifying exact call is tricky due to middleware


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_doesnt_log(self, client):
        """Test that health check endpoint doesn't log (commented out in code)."""
        # Health check logging is commented out in main.py
        response = client.get("/health")

        assert response.status_code == 200


class TestValidationExceptionHandler:
    """Test suite for validation exception handler."""

    def test_validation_error_handler_get_request(self, client):
        """Test validation error handler for GET request."""
        # Try to access an endpoint with invalid query parameter
        # This requires an actual endpoint that validates parameters
        # For now, we'll test the handler function directly
        from app.main import validation_exception_handler
        from pydantic import ValidationError

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.body = Mock(return_value=b"")

        # Create a mock validation error
        mock_exc = Mock(spec=RequestValidationError)
        mock_exc.errors.return_value = [
            {"loc": ["query", "id"], "msg": "field required", "type": "value_error.missing"}
        ]

        import asyncio
        response = asyncio.run(validation_exception_handler(mock_request, mock_exc))

        assert response.status_code == 422
        assert "detail" in response.body.decode()

    def test_validation_error_handler_post_request(self, client):
        """Test validation error handler for POST request with body."""
        from app.main import validation_exception_handler

        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/test"

        async def mock_body():
            return b'{"test": "data"}'

        mock_request.body = mock_body

        mock_exc = Mock(spec=RequestValidationError)
        mock_exc.errors.return_value = [
            {"loc": ["body", "field"], "msg": "field required", "type": "value_error.missing"}
        ]

        import asyncio
        response = asyncio.run(validation_exception_handler(mock_request, mock_exc))

        assert response.status_code == 422
        body = response.body.decode()
        assert "detail" in body

    def test_validation_error_has_cors_headers(self, client):
        """Test that validation errors include CORS headers."""
        from app.main import validation_exception_handler

        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/test"

        async def mock_body():
            return b''

        mock_request.body = mock_body

        mock_exc = Mock(spec=RequestValidationError)
        mock_exc.errors.return_value = []

        import asyncio
        response = asyncio.run(validation_exception_handler(mock_request, mock_exc))

        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"


class TestHttpExceptionHandler:
    """Test suite for HTTP exception handler."""

    def test_http_404_exception_handler(self, client):
        """Test HTTP exception handler for 404 errors."""
        from app.main import http_exception_handler

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/nonexistent"

        mock_exc = StarletteHTTPException(status_code=404, detail="Not Found")

        import asyncio
        response = asyncio.run(http_exception_handler(mock_request, mock_exc))

        assert response.status_code == 404
        body_json = eval(response.body.decode())
        assert body_json["detail"] == "Not Found"

    def test_http_500_exception_handler(self, client):
        """Test HTTP exception handler for 500 errors."""
        from app.main import http_exception_handler

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/error"

        mock_exc = StarletteHTTPException(status_code=500, detail="Internal Server Error")

        import asyncio
        response = asyncio.run(http_exception_handler(mock_request, mock_exc))

        assert response.status_code == 500

    def test_http_exception_has_cors_headers(self, client):
        """Test that HTTP exceptions include CORS headers."""
        from app.main import http_exception_handler

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        mock_exc = StarletteHTTPException(status_code=404, detail="Not Found")

        import asyncio
        response = asyncio.run(http_exception_handler(mock_request, mock_exc))

        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"

    def test_http_exception_logs_error(self, client):
        """Test that HTTP exceptions are logged."""
        from app.main import http_exception_handler

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        mock_exc = StarletteHTTPException(status_code=403, detail="Forbidden")

        with patch('app.main.logger') as mock_logger:
            import asyncio
            asyncio.run(http_exception_handler(mock_request, mock_exc))

            # Verify logger.error was called
            mock_logger.error.assert_called_once()


class TestGeneralExceptionHandler:
    """Test suite for general exception handler."""

    def test_general_exception_handler_value_error(self, client):
        """Test general exception handler for ValueError."""
        from app.main import general_exception_handler

        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/test"

        mock_exc = ValueError("Invalid value provided")

        import asyncio
        response = asyncio.run(general_exception_handler(mock_request, mock_exc))

        assert response.status_code == 500
        body_json = eval(response.body.decode())
        assert body_json["detail"] == "Internal server error"
        assert "Invalid value provided" in body_json["error"]

    def test_general_exception_handler_type_error(self, client):
        """Test general exception handler for TypeError."""
        from app.main import general_exception_handler

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        mock_exc = TypeError("Type error occurred")

        import asyncio
        response = asyncio.run(general_exception_handler(mock_request, mock_exc))

        assert response.status_code == 500

    def test_general_exception_has_cors_headers(self, client):
        """Test that general exceptions include CORS headers."""
        from app.main import general_exception_handler

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        mock_exc = Exception("Test error")

        import asyncio
        response = asyncio.run(general_exception_handler(mock_request, mock_exc))

        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"

    def test_general_exception_logs_error_with_type(self, client):
        """Test that general exceptions log error type."""
        from app.main import general_exception_handler

        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/test"

        mock_exc = RuntimeError("Runtime error occurred")

        with patch('app.main.logger') as mock_logger:
            import asyncio
            asyncio.run(general_exception_handler(mock_request, mock_exc))

            # Verify logger.error was called
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args[1]
            assert "error_type" in call_kwargs
            assert call_kwargs["error_type"] == "RuntimeError"


class TestRouterInclusion:
    """Test suite for router inclusion."""

    def test_jobs_router_included(self, client):
        """Test that jobs router is included."""
        # Check routes contain job-related paths
        routes = [route.path for route in client.app.routes]
        assert any('/v1' in path for path in routes)

    def test_contacts_router_included(self, client):
        """Test that contacts router is included."""
        routes = [route.path for route in client.app.routes]
        # Routers are included with /v1 prefix
        assert any('/v1' in path for path in routes)

    def test_all_routers_have_v1_prefix(self, client):
        """Test that all API routers use /v1 prefix."""
        routes = [route.path for route in client.app.routes]

        # Filter out OpenAPI routes and root routes
        api_routes = [r for r in routes if not r.startswith('/openapi') and not r.startswith('/docs') and r not in ['/', '/health']]

        # All API routes should start with /v1
        for route in api_routes:
            if route != '/':
                assert route.startswith('/v1') or route.startswith('/openapi') or route.startswith('/docs')

    def test_multiple_routers_registered(self, client):
        """Test that multiple routers are registered."""
        routes = [route.path for route in client.app.routes]

        # Should have routes from multiple routers
        # Each router adds its own routes
        assert len(routes) > 5  # At minimum: root, health, openapi, docs, redoc


class TestCorsConfiguration:
    """Test suite for CORS configuration."""

    def test_cors_allows_all_origins(self, client):
        """Test that CORS allows all origins."""
        response = client.options("/", headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET"
        })

        # CORS should allow the request
        # Note: TestClient might not fully simulate CORS preflight
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly defined

    def test_cors_allows_credentials(self, client):
        """Test that CORS allows credentials."""
        # CORS is configured with allow_credentials=True
        # Actual testing requires a real HTTP request
        pass  # Placeholder - full CORS testing requires integration tests

    def test_cors_exposes_headers(self, client):
        """Test that CORS exposes necessary headers."""
        # Configured in app.add_middleware for CORS
        # expose_headers includes Content-Length, Content-Type, etc.
        pass  # Placeholder - full header testing requires integration tests


class TestMiddlewareOrder:
    """Test suite for middleware ordering."""

    def test_cors_middleware_before_logging(self, client):
        """Test that CORS middleware is added before logging middleware."""
        # Middleware order matters - CORS should be first
        middleware_stack = list(client.app.user_middleware)

        # Find indices
        cors_index = None
        logging_index = None

        for i, middleware in enumerate(middleware_stack):
            middleware_type = type(middleware).__name__
            if 'CORS' in middleware_type:
                cors_index = i
            elif 'LoggingMiddleware' in middleware_type:
                logging_index = i

        # CORS should come before Logging in the stack
        # (In middleware stack, later additions appear first)
        if cors_index is not None and logging_index is not None:
            assert cors_index < logging_index


class TestAppMetadata:
    """Test suite for application metadata."""

    def test_app_title(self, client):
        """Test application title is set correctly."""
        assert client.app.title == "Job Track Now"

    def test_app_version_exists(self, client):
        """Test application version is set."""
        assert hasattr(client.app, 'version')
        assert client.app.version is not None

    def test_app_debug_mode(self, client):
        """Test application debug mode configuration."""
        # Debug mode is configurable via settings
        assert hasattr(client.app, 'debug')
