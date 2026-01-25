from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy import text
from typing import List

from ..utils.oauth_utils import verify_access_token
from ..utils.logger import logger
from ..core.database import SessionLocal


# Paths that don't require authentication
EXCLUDED_PATHS = [
    "/v1/authorize",      # OAuth authorization endpoint
    "/v1/login",          # OAuth login endpoint
    "/v1/token",          # OAuth token exchange endpoint
    "/v1/user/empty",     # Check if users table is empty (for initial setup)
    "/health",            # Health check endpoint
    "/",                  # Root endpoint
    "/docs",              # API documentation
    "/redoc",             # Alternative API documentation
    "/openapi.json"       # OpenAPI schema
]

# Paths that require conditional authentication (only when users exist)
# These paths are allowed without auth when no users exist in the database
CONDITIONAL_PATHS = [
    "/v1/user"            # User creation/update - allowed without auth when no users exist
]


def _check_users_empty() -> bool:
    """Check if users table is empty (for conditional auth paths)."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(user_id) as cnt FROM users")).first()
        return result.cnt == 0 if result else True
    except Exception as e:
        logger.error("Failed to check users table in middleware", error=str(e))
        return False
    finally:
        db.close()


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JWT tokens on all requests except excluded paths
    """

    def __init__(self, app, excluded_paths: List[str] = None):
        """
        Initialize JWT authentication middleware

        Args:
            app: FastAPI application
            excluded_paths: List of path prefixes to exclude from authentication
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or []

    async def dispatch(self, request: Request, call_next):
        """
        Process each request and validate JWT token

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            Response from next handler or 401 error
        """
        # Check if request path should be excluded from authentication
        path = request.url.path

        # Exclude authentication for specific paths
        for excluded_path in EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                #logger.debug(f"Skipping JWT validation for excluded path", path=path)
                return await call_next(request)

        # Check conditional paths - allow without auth if no users exist
        for conditional_path in CONDITIONAL_PATHS:
            if path.startswith(conditional_path):
                # Only allow POST (create) without auth when no users exist
                if request.method == "POST" and _check_users_empty():
                    logger.info("Allowing unauthenticated user creation (no users exist)", path=path)
                    return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(f"Missing Authorization header", path=path, method=request.method)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(f"Invalid Authorization header format", path=path, method=request.method)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]

        # Verify token
        payload = verify_access_token(token)
        if not payload:
            logger.warning(f"Invalid or expired token", path=path, method=request.method)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Token is valid - attach user info to request state for use in handlers
        request.state.user = payload
        logger.debug(f"JWT validated successfully",
                    path=path,
                    method=request.method,
                    username=payload.get("preferred_username"))

        # Continue to next handler
        return await call_next(request)
